package upx6.makercraft;
//MakerCraft 7.0 03/10/2026

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;

import net.minecraft.resources.Identifier;

import upx6.makercraft.block.ModBlocks;
import upx6.makercraft.item.ModItems;
import upx6.makercraft.serial.SerialManager;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;

import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;

import upx6.makercraft.block.ArduinoOutputBlock;

import net.minecraft.core.BlockPos;

import upx6.makercraft.data.ArduinoOutputData;
import upx6.makercraft.data.ModSavedData;

import java.util.UUID;

import net.minecraft.world.InteractionResult;
import net.minecraft.world.InteractionHand;
import net.minecraft.network.chat.Component;


public class MakerCraft implements ModInitializer {

    public static final String MOD_ID = "makercraft";

    public static final Logger LOGGER =
            LoggerFactory.getLogger(MOD_ID);

    public static volatile String lastSerialMessage = null;

    private static boolean savedDataTested = false;

    @Override
    public void onInitialize() {

        ModBlocks.initialize();

        ModItems.initialize();


        // ======================================================
        // IDENTIFICAÇÃO DO ARDUINO OUTPUT
        // CLIQUE DIREITO
        // ======================================================

        UseBlockCallback.EVENT.register(
                (player, level, hand, hitResult) -> {

                    // ==================================================
                    // SÓ QUEREMOS A MÃO PRINCIPAL
                    // ==================================================

                    if (hand != InteractionHand.MAIN_HAND) {

                        return InteractionResult.PASS;
                    }


                    // ==================================================
                    // SHIFT + CLIQUE DIREITO
                    //
                    // Permite a interação normal do Minecraft.
                    //
                    // Isso permite:
                    // - colocar blocos
                    // - colocar botões
                    // - colocar alavancas
                    // - colocar outros blocos
                    // ==================================================

                    if (player.isShiftKeyDown()) {

                        return InteractionResult.PASS;
                    }


                    // ==================================================
                    // SÓ EXECUTA NO SERVIDOR
                    // ==================================================

                    if (level.isClientSide()) {

                        return InteractionResult.SUCCESS;
                    }


                    // ==================================================
                    // POSIÇÃO DO BLOCO CLICADO
                    // ==================================================

                    BlockPos pos =
                            hitResult.getBlockPos();


                    // ==================================================
                    // ESTADO DO BLOCO
                    // ==================================================

                    BlockState state =
                            level.getBlockState(pos);


                    // ==================================================
                    // VERIFICA SE É ARDUINO OUTPUT
                    // ==================================================

                    if (!(state.getBlock()
                            instanceof ArduinoOutputBlock)) {

                        return InteractionResult.PASS;
                    }


                    // ==================================================
                    // SAVED DATA
                    // ==================================================

                    ServerLevel serverLevel =
                            (ServerLevel) level;


                    ArduinoOutputData data =
                            ModSavedData.get(
                                    serverLevel
                            );


                    // ==================================================
                    // PROCURA O OUTPUT PELA POSIÇÃO
                    // ==================================================

                    ArduinoOutputData.OutputEntry output =
                            data.findOutputAt(
                                    pos.getX(),
                                    pos.getY(),
                                    pos.getZ(),
                                    level.dimension().toString()
                            );


                    // ==================================================
                    // NÃO ENCONTROU
                    // ==================================================

                    if (output == null) {

                        player.displayClientMessage(
                                Component.literal(
                                        "§cArduino Output não registrado!"
                                ),
                                false
                        );


                        return InteractionResult.SUCCESS;
                    }


                    // ==================================================
                    // MOSTRA O NÚMERO
                    // ==================================================

                    player.displayClientMessage(
                            Component.literal(
                                    "§aArduino Output"
                                            + " §7| §fNº: "
                                            + output.getNumber()
                            ),
                            false
                    );


                    // ==================================================
                    // IMPEDE O CLIQUE NORMAL
                    // ==================================================

                    return InteractionResult.SUCCESS;
                }
        );


        LOGGER.info(
                "MakerCraft inicializado!"
        );


        // ======================================================
        // PORTAS SERIAIS
        // ======================================================

        LOGGER.info(
                "Portas seriais disponíveis:"
        );


        for (var port :
                SerialManager.getAvailablePorts()) {

            LOGGER.info(
                    "Porta: {} | Descrição: {}",
                    port.getSystemPortName(),
                    port.getDescriptivePortName()
            );
        }


        // ======================================================
        // CONEXÃO COM ARDUINO
        // ======================================================

        boolean connected = false;


        for (var port :
                SerialManager.getAvailablePorts()) {

            String portName =
                    port.getSystemPortName();


            LOGGER.info(
                    "Tentando conectar na porta {}...",
                    portName
            );


            if (SerialManager.connect(portName)) {

                LOGGER.info(
                        "Arduino conectado na porta {}.",
                        portName
                );


                connected = true;


                try {

                    Thread.sleep(2000);

                } catch (InterruptedException e) {

                    Thread.currentThread()
                            .interrupt();
                }


                SerialManager.sendTestMessage(
                        "HELLO_ARDUINO"
                );


                break;
            }
        }


        if (!connected) {

            LOGGER.error(
                    "Não foi possível conectar a nenhuma porta serial."
            );
        }


        // ======================================================
        // THREAD DO ARDUINO
        // ======================================================

        Thread serialReader =
                new Thread(() -> {

                    while (true) {

                        String message =
                                SerialManager.readMessage();


                        if (message != null
                                && !message.isEmpty()) {

                            LOGGER.info(
                                    "Arduino enviou: {}",
                                    message
                            );


                            lastSerialMessage =
                                    message;
                        }


                        try {

                            Thread.sleep(20);

                        } catch (InterruptedException e) {

                            Thread.currentThread()
                                    .interrupt();

                            break;
                        }
                    }

                },
                        "MakerCraft-SerialReader");


        serialReader.setDaemon(true);

        serialReader.start();


        // ======================================================
        // PROCESSAMENTO DAS MENSAGENS DO ARDUINO
        // ======================================================

        ServerTickEvents.END_SERVER_TICK.register(
                server -> {

                    String message =
                            lastSerialMessage;


                    if (message == null) {
                        return;
                    }


                    lastSerialMessage = null;


                    LOGGER.info(
                            "Processando mensagem do Arduino: {}",
                            message
                    );


                    // ==================================================
                    // PROTOCOLO DE OUTPUT
                    // ==================================================

                    if (message.startsWith("OUTPUT:")) {

                        processOutputMessage(
                                server,
                                message
                        );


                        return;
                    }


                    // ==================================================
                    // SISTEMA ANTIGO
                    // ==================================================

                    if (ArduinoOutputBlock.outputBlockPos != null
                            && ArduinoOutputBlock.outputBlockDimension != null) {

                        ServerLevel level =
                                server.getLevel(
                                        ArduinoOutputBlock
                                                .outputBlockDimension
                                );


                        if (level != null) {

                            BlockPos pos =
                                    ArduinoOutputBlock
                                            .outputBlockPos;


                            BlockState state =
                                    level.getBlockState(pos);


                            if (state.getBlock()
                                    instanceof ArduinoOutputBlock) {


                                if (message.equals(
                                        "ARDUINO_ON")) {

                                    level.setBlock(
                                            pos,

                                            state.setValue(
                                                    BlockStateProperties.POWERED,
                                                    true
                                            ),

                                            3
                                    );


                                    LOGGER.info(
                                            "Arduino Output ligado!"
                                    );
                                }


                                if (message.equals(
                                        "ARDUINO_OFF")) {

                                    level.setBlock(
                                            pos,

                                            state.setValue(
                                                    BlockStateProperties.POWERED,
                                                    false
                                            ),

                                            3
                                    );


                                    LOGGER.info(
                                            "Arduino Output desligado!"
                                    );
                                }
                            }
                        }
                    }
                }
        );


        // ======================================================
        // DETECTA OUTPUT QUEBRADO
        // ======================================================

        PlayerBlockBreakEvents.AFTER.register(
                (level, player, pos, state, blockEntity) -> {

                    if (level.isClientSide()) {
                        return;
                    }


                    if (!(state.getBlock()
                            instanceof ArduinoOutputBlock)) {

                        return;
                    }


                    ServerLevel serverLevel =
                            (ServerLevel) level;


                    ArduinoOutputData data =
                            ModSavedData.get(
                                    serverLevel
                            );


                    data.removeOutputAt(
                            pos.getX(),
                            pos.getY(),
                            pos.getZ(),
                            level.dimension().toString()
                    );


                    if (ArduinoOutputBlock.outputBlockPos != null
                            && ArduinoOutputBlock.outputBlockPos.equals(pos)) {

                        ArduinoOutputBlock.outputBlockPos =
                                null;

                        ArduinoOutputBlock.outputBlockDimension =
                                null;
                    }


                    LOGGER.info(
                            "Arduino Output removido do SavedData: {}",
                            pos
                    );
                }
        );


        // ======================================================
        // VERIFICA SAVED DATA
        // ======================================================

        ServerTickEvents.END_SERVER_TICK.register(
                server -> {

                    if (savedDataTested) {
                        return;
                    }


                    savedDataTested = true;


                    ServerLevel level =
                            server.overworld();


                    ArduinoOutputData data =
                            ModSavedData.get(level);


                    LOGGER.info(
                            "========================================"
                    );


                    LOGGER.info(
                            "VERIFICANDO TODOS OS ARDUINO OUTPUTS"
                    );


                    LOGGER.info(
                            "========================================"
                    );


                    var outputs =
                            data.getOutputs();


                    if (outputs.isEmpty()) {

                        LOGGER.info(
                                "SavedData está vazio."
                        );


                    } else {

                        LOGGER.info(
                                "Quantidade de Outputs encontrados: {}",
                                outputs.size()
                        );


                        int contador = 1;


                        for (
                                ArduinoOutputData.OutputEntry output :
                                outputs
                        ) {

                            LOGGER.info(
                                    "OUTPUT #{} | Nº={} | ID={} | X={} Y={} Z={} | Dimensão={}",
                                    contador,
                                    output.getNumber(),
                                    output.getId(),
                                    output.getX(),
                                    output.getY(),
                                    output.getZ(),
                                    output.getDimension()
                            );


                            contador++;
                        }
                    }


                    LOGGER.info(
                            "========================================"
                    );
                }
        );
    }


    // ==========================================================
    // PROCESSA OUTPUT:UUID:ON/OFF
    // ==========================================================

    private static void processOutputMessage(
            MinecraftServer server,
            String message
    ) {

        LOGGER.info(
                "========================================"
        );


        LOGGER.info(
                "MENSAGEM DE OUTPUT RECEBIDA!"
        );


        LOGGER.info(
                "Mensagem: {}",
                message
        );


        // ======================================================
        // SEPARA A MENSAGEM
        // ======================================================

        String[] parts =
                message.split(":");


        if (parts.length != 3) {

            LOGGER.error(
                    "Formato inválido!"
            );


            LOGGER.error(
                    "Formato esperado: OUTPUT:NÚMERO:ON ou OUTPUT:NÚMERO:OFF"
            );


            return;
        }


        // ======================================================
        // CONVERTE NÚMERO DO OUTPUT
        // ======================================================

        int outputNumber;


        try {

            outputNumber =
                    Integer.parseInt(
                            parts[1]
                    );


        } catch (NumberFormatException e) {

            LOGGER.error(
                    "Número de Output inválido: {}",
                    parts[1]
            );


            return;
        }


        String command =
                parts[2];


        // ======================================================
        // VALIDA COMANDO
        // ======================================================

        boolean turnOn;


        if (command.equals("ON")) {

            turnOn = true;


        } else if (command.equals("OFF")) {

            turnOn = false;


        } else {

            LOGGER.error(
                    "Comando inválido: {}",
                    command
            );


            return;
        }


        // ======================================================
        // PROCURA NO SAVED DATA
        // ======================================================

        ServerLevel overworld =
                server.overworld();


        ArduinoOutputData data =
                ModSavedData.get(overworld);


        ArduinoOutputData.OutputEntry output =
                data.findOutputByNumber(
                        outputNumber
                );


        if (output == null) {

            LOGGER.error(
                    "Output Nº {} não encontrado no SavedData!",
                    outputNumber
            );


            return;
        }


        // ======================================================
        // RECUPERA POSIÇÃO
        // ======================================================

        BlockPos pos =
                output.getBlockPos();


        // ======================================================
        // RECUPERA DIMENSÃO
        // ======================================================

        ServerLevel targetLevel;


        if (output.getDimension()
                .contains("the_nether")) {

            targetLevel =
                    server.getLevel(
                            net.minecraft.world.level.Level.NETHER
                    );


        } else if (output.getDimension()
                .contains("the_end")) {

            targetLevel =
                    server.getLevel(
                            net.minecraft.world.level.Level.END
                    );


        } else {

            targetLevel =
                    server.getLevel(
                            net.minecraft.world.level.Level.OVERWORLD
                    );
        }


        if (targetLevel == null) {

            LOGGER.error(
                    "A dimensão do Output não está disponível!"
            );


            return;
        }


        // ======================================================
        // VERIFICA BLOCO
        // ======================================================

        BlockState state =
                targetLevel.getBlockState(pos);


        LOGGER.info(
                "Bloco encontrado na posição: {}",
                state.getBlock()
        );


        if (!(state.getBlock()
                instanceof ArduinoOutputBlock)) {

            LOGGER.error(
                    "O bloco salvo não é um ArduinoOutputBlock!"
            );


            return;
        }


        // ======================================================
        // ALTERA POWERED
        // ======================================================

        BlockState newState =
                state.setValue(
                        BlockStateProperties.POWERED,
                        turnOn
                );


        targetLevel.setBlock(
                pos,
                newState,
                3
        );


        // ======================================================
        // RESULTADO
        // ======================================================

        LOGGER.info(
                "========================================"
        );


        if (turnOn) {

            LOGGER.info(
                    "ARDUINO OUTPUT LIGADO!"
            );


        } else {

            LOGGER.info(
                    "ARDUINO OUTPUT DESLIGADO!"
            );
        }


        LOGGER.info(
                "Número: {}",
                outputNumber
        );


        LOGGER.info(
                "Posição: {}",
                pos
        );


        LOGGER.info(
                "========================================"
        );
    }


    // ==========================================================
    // ID DO MOD
    // ==========================================================

    public static Identifier id(
            String path
    ) {

        return Identifier.fromNamespaceAndPath(
                MOD_ID,
                path
        );
    }
}

