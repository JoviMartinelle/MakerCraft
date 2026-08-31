package upx6.makercraft.block;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;

import net.minecraft.server.level.ServerLevel;

import upx6.makercraft.data.ArduinoOutputData;
import upx6.makercraft.data.ModSavedData;

import java.util.UUID;


public class ArduinoOutputBlock extends Block {

    // ==========================================================
    // OUTPUT ATUAL
    // ==========================================================

    public static BlockPos outputBlockPos = null;

    public static ResourceKey<Level> outputBlockDimension = null;


    // ==========================================================
    // CONSTRUTOR
    // ==========================================================

    public ArduinoOutputBlock(Properties properties) {

        super(properties);

        this.registerDefaultState(
                this.stateDefinition.any()
                        .setValue(
                                BlockStateProperties.POWERED,
                                false
                        )
        );
    }


    // ==========================================================
    // BLOCK STATE
    // ==========================================================

    @Override
    protected void createBlockStateDefinition(
            StateDefinition.Builder<Block, BlockState> builder
    ) {

        builder.add(
                BlockStateProperties.POWERED
        );
    }


    // ==========================================================
    // É FONTE DE REDSTONE
    // ==========================================================

    @Override
    protected boolean isSignalSource(
            BlockState state
    ) {

        return true;
    }


    // ==========================================================
    // SINAL DE REDSTONE
    // ==========================================================

    @Override
    protected int getSignal(
            BlockState state,
            BlockGetter level,
            BlockPos pos,
            Direction direction
    ) {

        return state.getValue(
                BlockStateProperties.POWERED
        ) ? 15 : 0;
    }


    // ==========================================================
    // QUANDO O BLOCO É COLOCADO
    // ==========================================================

    @Override
    protected void onPlace(
            BlockState state,
            Level level,
            BlockPos pos,
            BlockState oldState,
            boolean movedByPiston
    ) {

        super.onPlace(
                state,
                level,
                pos,
                oldState,
                movedByPiston
        );


        // ======================================================
        // SÓ EXECUTA NO SERVIDOR
        // ======================================================

        if (level.isClientSide()) {
            return;
        }


        ServerLevel serverLevel =
                (ServerLevel) level;


        // ======================================================
        // SALVA O OUTPUT ATUAL
        // ======================================================

        outputBlockPos = pos;

        outputBlockDimension =
                level.dimension();


        // ======================================================
        // PEGA O SAVED DATA
        // ======================================================

        ArduinoOutputData data =
                ModSavedData.get(
                        serverLevel
                );


        // ======================================================
        // VERIFICA SE JÁ EXISTE OUTPUT NESSA POSIÇÃO
        // ======================================================

        ArduinoOutputData.OutputEntry existingOutput =
                data.findOutputAt(
                        pos.getX(),
                        pos.getY(),
                        pos.getZ(),
                        level.dimension().toString()
                );


        // ======================================================
        // SE JÁ EXISTE
        // ======================================================

        if (existingOutput != null) {

            System.out.println(
                    "========================================"
            );

            System.out.println(
                    "ARDUINO OUTPUT JÁ REGISTRADO!"
            );

            System.out.println(
                    "Número: OUTPUT #"
                            + existingOutput.getNumber()
            );

            System.out.println(
                    "Mantendo UUID existente:"
            );

            System.out.println(
                    "ID: "
                            + existingOutput.getId()
            );

            System.out.println(
                    "Posição: "
                            + pos
            );

            System.out.println(
                    "========================================"
            );

            return;
        }


        // ======================================================
        // CRIA NOVA UUID
        // ======================================================

        UUID outputId =
                UUID.randomUUID();


        // ======================================================
        // SALVA NO SAVED DATA
        // ======================================================

        data.setOutput(
                outputId,
                pos.getX(),
                pos.getY(),
                pos.getZ(),
                level.dimension().toString()
        );


        // ======================================================
        // RECUPERA O OUTPUT RECÉM-CRIADO
        // ======================================================

        ArduinoOutputData.OutputEntry newOutput =
                data.findOutputAt(
                        pos.getX(),
                        pos.getY(),
                        pos.getZ(),
                        level.dimension().toString()
                );


        // ======================================================
        // LOG
        // ======================================================

        System.out.println(
                "========================================"
        );

        System.out.println(
                "ARDUINO OUTPUT REGISTRADO!"
        );

        if (newOutput != null) {

            System.out.println(
                    "Número: OUTPUT #"
                            + newOutput.getNumber()
            );
        }

        System.out.println(
                "ID: "
                        + outputId
        );

        System.out.println(
                "Posição: "
                        + pos
        );

        System.out.println(
                "Dimensão: "
                        + level.dimension()
        );

        System.out.println(
                "TOTAL DE OUTPUTS NO SAVED DATA AGORA: "
                        + data.getOutputs().size()
        );

        System.out.println(
                "========================================"
        );
    }


    // ==========================================================
    // BOTÃO ESQUERDO
    //
    // IMPORTANTE:
    // Não usamos @Override aqui.
    //
    // Esse método será chamado pela própria lógica do bloco
    // quando o jogador atacar/interagir com ele.
    // ==========================================================

    protected void attack(
            BlockState state,
            Level level,
            BlockPos pos,
            Player player
    ) {

        // ======================================================
        // SÓ EXECUTA NO SERVIDOR
        // ======================================================

        if (level.isClientSide()) {
            return;
        }


        ServerLevel serverLevel =
                (ServerLevel) level;


        // ======================================================
        // PEGA O SAVED DATA
        // ======================================================

        ArduinoOutputData data =
                ModSavedData.get(
                        serverLevel
                );


        // ======================================================
        // PROCURA O OUTPUT
        // ======================================================

        ArduinoOutputData.OutputEntry output =
                data.findOutputAt(
                        pos.getX(),
                        pos.getY(),
                        pos.getZ(),
                        level.dimension().toString()
                );


        // ======================================================
        // SE NÃO ENCONTROU
        // ======================================================

        if (output == null) {

            player.displayClientMessage(
                    net.minecraft.network.chat.Component.literal(
                            "§cArduino Output não registrado!"
                    ),
                    true
            );

            return;
        }


        // ======================================================
        // MOSTRA SOMENTE O NÚMERO
        // ======================================================

        player.displayClientMessage(
                net.minecraft.network.chat.Component.literal(
                        "§aArduino Output §f#"
                                + output.getNumber()
                ),
                true
        );
    }
}


