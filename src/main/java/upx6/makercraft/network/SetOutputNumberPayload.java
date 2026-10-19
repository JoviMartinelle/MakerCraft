package upx6.makercraft.network;

import net.minecraft.core.BlockPos;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import upx6.makercraft.MakerCraft;

public record SetOutputNumberPayload(BlockPos pos, int number) implements CustomPacketPayload {

    public static final Type<SetOutputNumberPayload> TYPE =
            new Type<>(MakerCraft.id("set_output_number"));

    public static final StreamCodec<RegistryFriendlyByteBuf, SetOutputNumberPayload> CODEC =
            StreamCodec.composite(
                    BlockPos.STREAM_CODEC,
                    SetOutputNumberPayload::pos,
                    ByteBufCodecs.VAR_INT,
                    SetOutputNumberPayload::number,
                    SetOutputNumberPayload::new
            );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
