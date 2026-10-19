package upx6.makercraft.network;

import net.minecraft.core.BlockPos;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import upx6.makercraft.MakerCraft;

public record OpenOutputNumberPayload(BlockPos pos, int number) implements CustomPacketPayload {

    public static final Type<OpenOutputNumberPayload> TYPE =
            new Type<>(MakerCraft.id("open_output_number"));

    public static final StreamCodec<RegistryFriendlyByteBuf, OpenOutputNumberPayload> CODEC =
            StreamCodec.composite(
                    BlockPos.STREAM_CODEC,
                    OpenOutputNumberPayload::pos,
                    ByteBufCodecs.VAR_INT,
                    OpenOutputNumberPayload::number,
                    OpenOutputNumberPayload::new
            );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
