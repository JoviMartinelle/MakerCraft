package upx6.makercraft.block;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.redstone.Orientation;

import net.minecraft.core.Direction;
import net.minecraft.world.level.BlockGetter;
import upx6.makercraft.serial.SerialManager;

public class ArduinoBlock extends Block {

    public ArduinoBlock(Properties properties) {
        super(properties);

        this.registerDefaultState(
                this.stateDefinition.any()
                        .setValue(BlockStateProperties.POWERED, false)
        );
    }

    @Override
    protected void createBlockStateDefinition(
            StateDefinition.Builder<Block, BlockState> builder
    ) {
        builder.add(BlockStateProperties.POWERED);
    }

    @Override
    protected boolean isSignalSource(BlockState state) {
        return true;
    }

    @Override
    protected int getSignal(
            BlockState state,
            BlockGetter level,
            BlockPos pos,
            Direction direction
    ) {
        return state.getValue(BlockStateProperties.POWERED) ? 15 : 0;
    }

    @Override
    protected void neighborChanged(
            BlockState state,
            Level level,
            BlockPos pos,
            Block sourceBlock,
            Orientation orientation,
            boolean notify
    ) {
        super.neighborChanged(
                state,
                level,
                pos,
                sourceBlock,
                orientation,
                notify
        );

        if (!level.isClientSide()) {

            int signal = level.getBestNeighborSignal(pos);

            System.out.println(
                    "Arduino Block - Sinal de Redstone: " + signal
            );

            SerialManager.sendTestMessage(
                    "REDSTONE_LEVEL:" + signal
            );
        }
    }
}