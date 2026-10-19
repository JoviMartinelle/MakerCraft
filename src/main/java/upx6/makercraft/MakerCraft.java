package upx6.makercraft;
//MakerCraft 7.0 03/10/2026

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;

import net.minecraft.resources.Identifier;

import upx6.makercraft.block.ModBlockEntities;
import upx6.makercraft.block.ModBlocks;
import upx6.makercraft.item.ModItems;
import upx6.makercraft.network.ModNetworking;
import upx6.makercraft.network.OpenOutputNumberPayload;
import upx6.makercraft.serial.SerialManager;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import upx6.makercraft.serial.FirmwareInstaller;

import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;

import upx6.makercraft.block.ArduinoOutputBlock;

import net.minecraft.core.BlockPos;

import upx6.makercraft.data.ArduinoOutputData;
import upx6.makercraft.data.ModSavedData;

import java.util.Queue;
import java.util.UUID;
import java.util.concurrent.ConcurrentLinkedQueue;

import net.minecraft.world.InteractionResult;
import net.minecraft.world.InteractionHand;
import net.minecraft.network.chat.Component;


public class MakerCraft implements ModInitializer {

    public static final String MOD_ID = "makercraft";

    public static final Logger LOGGER =
            LoggerFactory.getLogger(MOD_ID);

    private static final Queue<String> incomingMessages =
            new ConcurrentLinkedQueue<>();

    private static String lastQueuedMessage;

    private static volatile MinecraftServer currentServer;

    private static volatile String startupNotice;

    private static boolean savedDataTested = false;

    @Override
    public void onInitialize() {

        ModBlocks.initialize();

        ModBlockEntities.initialize();

        ModItems.initialize();

        ModNetworking.register();


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

                    BlockPos pos =
                            hitResult.getBlockPos();

                    BlockState state =
                            level.getBlockState(pos);

                    boolean handsFree =
                            player.getMainHandItem().isEmpty()
                                    && player.getOffhandItem().isEmpty();

                    if (player.isShiftKeyDown()) {

                        if (!(state.getBlock() instanceof ArduinoOutputBlock) || !handsFree) {
                            return InteractionResult.PASS;
                        }

                        if (level.isClientSide()) {
                            return InteractionResult.SUCCESS;
                        }

                        return openOutputNumberEditor(
                                (ServerPlayer) player,
                                (ServerLevel) level,
                                pos
                        );
                    }


                    // ==================================================
                    // SÓ EXECUTA NO SERVIDOR
                    // ==================================================

                    if (level.isClientSide()) {

                        return InteractionResult.SUCCESS;
                    }


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
        // THREAD DO ARDUINO
        //
        // A conexão fica fora da thread de renderização.
        // writeBytes na COM1 (porta da placa-mãe) bloqueia
        // para sempre e o jogo nunca termina de iniciar.
        // ======================================================

        ServerLifecycleEvents.SERVER_STARTED.register(server -> currentServer = server);
        ServerLifecycleEvents.SERVER_STOPPED.register(server -> currentServer = null);
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            String notice = startupNotice;
            if (notice != null) {
                handler.getPlayer().displayClientMessage(Component.literal(notice), false);
            }
        });

        Thread serialReader =
                new Thread(() -> {

                    String portName = null;


                    for (var port :
                            SerialManager.getAvailablePorts()) {

                        if (!SerialManager.looksLikeArduino(port)) {
                            continue;
                        }


                        portName = port.getSystemPortName();
                        break;
                    }


                    if (portName == null) {

                        LOGGER.error(
                                "Nenhum Arduino encontrado. Portas como COM1 (Communications Port) são ignoradas."
                        );
                    } else {

                        LOGGER.info(
                                "Tentando conectar na porta {}...",
                                portName
                        );


                        try {

                            prepareArduino(portName);

                        } catch (InterruptedException e) {

                            Thread.currentThread()
                                    .interrupt();

                            return;
                        }
                    }


                    while (!Thread.currentThread().isInterrupted()) {

                        SerialManager.drainOutgoing();

                        String message =
                                SerialManager.readMessage();


                        int drained = 0;

                        while (message != null
                                && !message.isEmpty()
                                && drained < 64) {

                            if (!message.equals(lastQueuedMessage)) {
                                LOGGER.info(
                                        "Arduino enviou: {}",
                                        message
                                );

                                while (incomingMessages.size() >= 32) {
                                    incomingMessages.poll();
                                }

                                incomingMessages.add(message);
                                lastQueuedMessage = message;
                            }

                            drained++;
                            message = SerialManager.readMessage();
                        }


                        try {

                            Thread.sleep(drained == 0 ? 20 : 1);

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
                            incomingMessages.poll();


                    if (message == null) {
                        return;
                    }


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

    private void prepareArduino(String portName) throws InterruptedException {
        if (handshake(portName)) {
            LOGGER.info("Arduino pronto na porta {}.", portName);
            return;
        }

        SerialManager.disconnect();
        Thread.sleep(500);
        announce("Primeira vez com este Arduino: gravando o programa da placa. Pode levar alguns minutos.");

        if (!FirmwareInstaller.install(portName)) {
            announce("Não consegui gravar o Arduino. Confira o cabo e se a placa apareceu no computador.");
            return;
        }

        Thread.sleep(500);
        if (handshake(portName)) {
            announce("Arduino gravado. O computador do jogo já pode enviar os comandos.");
            return;
        }

        SerialManager.disconnect();
        announce("A placa foi gravada, mas não respondeu. Feche o monitor serial se ele estiver aberto.");
    }

    private boolean handshake(String portName) throws InterruptedException {
        if (!SerialManager.connect(portName)) {
            return false;
        }

        Thread.sleep(2000);
        SerialManager.sendTestMessage("HELLO_ARDUINO");
        long deadline = System.currentTimeMillis() + 3000;

        while (System.currentTimeMillis() < deadline) {
            String message = SerialManager.readMessage();
            if (FirmwareInstaller.READY.equals(message)) {
                return true;
            }
            Thread.sleep(40);
        }

        SerialManager.disconnect();
        return false;
    }

    private static void announce(String message) {
        startupNotice = message;
        LOGGER.info(message);
        MinecraftServer server = currentServer;
        if (server == null) {
            return;
        }

        server.execute(() -> {
            for (ServerPlayer player : server.getPlayerList().getPlayers()) {
                player.displayClientMessage(Component.literal(message), false);
            }
        });
    }

    private InteractionResult openOutputNumberEditor(
            ServerPlayer player,
            ServerLevel level,
            BlockPos pos
    ) {

        ArduinoOutputData data =
                ModSavedData.get(level);

        ArduinoOutputData.OutputEntry output =
                data.findOutputAt(
                        pos.getX(),
                        pos.getY(),
                        pos.getZ(),
                        level.dimension().toString()
                );

        if (output == null) {
            player.displayClientMessage(
                    Component.literal("Saída Arduino não registrada."),
                    false
            );
            return InteractionResult.SUCCESS;
        }

        ModNetworking.send(
                player,
                new OpenOutputNumberPayload(pos, output.getNumber())
        );
        return InteractionResult.SUCCESS;
    }


    public static Identifier id(
            String path
    ) {

        return Identifier.fromNamespaceAndPath(
                MOD_ID,
                path
        );
    }
}

