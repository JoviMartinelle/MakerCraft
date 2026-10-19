package upx6.makercraft.network;

import net.minecraft.core.BlockPos;
import net.minecraft.network.RegistryFriendlyByteBuf;
import com.mojang.datafixers.util.Function4;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import upx6.makercraft.MakerCraft;

public record SaveComputerPayload(BlockPos pos, String code, String locks, boolean execute) implements CustomPacketPayload {

    public static final Type<SaveComputerPayload> TYPE =
            new Type<>(MakerCraft.id("save_computer"));

    public static final StreamCodec<RegistryFriendlyByteBuf, SaveComputerPayload> CODEC =
            StreamCodec.composite(
                    BlockPos.STREAM_CODEC,
                    SaveComputerPayload::pos,
                    ByteBufCodecs.stringUtf8(ComputerPayloads.MAX_CODE_CHARS),
                    SaveComputerPayload::code,
                    ByteBufCodecs.stringUtf8(64),
                    SaveComputerPayload::locks,
                    ByteBufCodecs.BOOL,
                    SaveComputerPayload::execute,
                    (Function4<BlockPos, String, String, Boolean, SaveComputerPayload>) SaveComputerPayload::new
            );

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
