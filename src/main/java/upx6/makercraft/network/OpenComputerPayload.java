package upx6.makercraft.network;

import net.minecraft.core.BlockPos;
import net.minecraft.network.RegistryFriendlyByteBuf;
import com.mojang.datafixers.util.Function4;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import upx6.makercraft.MakerCraft;

public record OpenComputerPayload(BlockPos pos, String title, String code, String locks) implements CustomPacketPayload {

    public static final Type<OpenComputerPayload> TYPE =
            new Type<>(MakerCraft.id("open_computer"));

    public static final StreamCodec<RegistryFriendlyByteBuf, OpenComputerPayload> CODEC =
            StreamCodec.composite(
                    BlockPos.STREAM_CODEC,
                    OpenComputerPayload::pos,
                    ByteBufCodecs.stringUtf8(64),
                    OpenComputerPayload::title,
                    ByteBufCodecs.stringUtf8(ComputerPayloads.MAX_CODE_CHARS),
                    OpenComputerPayload::code,
                    ByteBufCodecs.stringUtf8(64),
                    OpenComputerPayload::locks,
                    (Function4<BlockPos, String, String, String, OpenComputerPayload>) OpenComputerPayload::new
            );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
