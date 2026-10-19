package upx6.makercraft.network;

import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import upx6.makercraft.block.ArduinoOutputBlock;
import upx6.makercraft.block.ComputerBlockEntity;
import upx6.makercraft.computer.ComputerLocks;
import upx6.makercraft.computer.ComputerProgram;
import upx6.makercraft.data.ArduinoOutputData;
import upx6.makercraft.data.ModSavedData;
import upx6.makercraft.serial.SerialManager;

public final class ModNetworking {

    private ModNetworking() {
    }

    public static void register() {
        PayloadTypeRegistry.playS2C().register(OpenComputerPayload.TYPE, OpenComputerPayload.CODEC);
        PayloadTypeRegistry.playC2S().register(SaveComputerPayload.TYPE, SaveComputerPayload.CODEC);
        PayloadTypeRegistry.playS2C().register(OpenOutputNumberPayload.TYPE, OpenOutputNumberPayload.CODEC);
        PayloadTypeRegistry.playC2S().register(SetOutputNumberPayload.TYPE, SetOutputNumberPayload.CODEC);

        ServerPlayNetworking.registerGlobalReceiver(SaveComputerPayload.TYPE, (payload, context) ->
                context.server().execute(() -> handleSave(context.player(), payload))
        );
        ServerPlayNetworking.registerGlobalReceiver(SetOutputNumberPayload.TYPE, (payload, context) ->
                context.server().execute(() -> handleSetNumber(context.player(), payload))
        );
    }

    public static void send(ServerPlayer player, CustomPacketPayload payload) {
        ServerPlayNetworking.send(player, payload);
    }

    private static void handleSave(ServerPlayer player, SaveComputerPayload payload) {
        if (!(player.level() instanceof ServerLevel level)) {
            return;
        }

        if (player.blockPosition().distSqr(payload.pos()) > 64) {
            return;
        }

        if (!(level.getBlockEntity(payload.pos()) instanceof ComputerBlockEntity computer)) {
            return;
        }

        String code = payload.code() == null ? "" : payload.code();
        if (code.length() > ComputerPayloads.MAX_CODE_CHARS) {
            code = code.substring(0, ComputerPayloads.MAX_CODE_CHARS);
        }

        if (player.isCreative()) {
            computer.setCode(code);
            computer.setLocks(ComputerLocks.fit(code, payload.locks()));
        } else {
            String kept = ComputerLocks.realign(computer.getCode(), computer.getLocks(), code, true);
            if (kept == null) {
                if (payload.execute()) {
                    player.displayClientMessage(
                            Component.literal("Uma linha trancada não pode ser alterada."),
                            false
                    );
                }
                return;
            }
            computer.setCode(code);
            computer.setLocks(kept);
        }

        computer.setChanged();

        if (!payload.execute()) {
            return;
        }

        String error = ComputerProgram.validate(code);
        if (error != null) {
            player.displayClientMessage(Component.literal(error), false);
            return;
        }

        if (!SerialManager.isConnected()) {
            player.displayClientMessage(
                    Component.literal("Arduino não conectado. O programa foi salvo no computador."),
                    false
            );
            return;
        }

        SerialManager.queueMessage(ComputerProgram.toProtocol(code));
        player.displayClientMessage(Component.literal("Programa enviado ao Arduino."), false);
    }

    private static void handleSetNumber(ServerPlayer player, SetOutputNumberPayload payload) {
        if (!(player.level() instanceof ServerLevel level)) {
            return;
        }

        BlockPos pos = payload.pos();
        if (player.blockPosition().distSqr(pos) > 64) {
            return;
        }

        if (!(level.getBlockState(pos).getBlock() instanceof ArduinoOutputBlock)) {
            return;
        }

        ArduinoOutputData data = ModSavedData.get(level);
        String error = data.setOutputNumber(
                pos.getX(),
                pos.getY(),
                pos.getZ(),
                level.dimension().toString(),
                payload.number()
        );

        if (error != null) {
            player.displayClientMessage(Component.literal(error), false);
            return;
        }

        player.displayClientMessage(
                Component.literal("Saída Arduino agora é o nº " + payload.number() + "."),
                false
        );
    }
}
