package upx6.makercraft.client;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import upx6.makercraft.network.OpenComputerPayload;
import upx6.makercraft.network.OpenOutputNumberPayload;

public class MakerCraftClient implements ClientModInitializer {

    @Override
    public void onInitializeClient() {
        ClientPlayNetworking.registerGlobalReceiver(OpenComputerPayload.TYPE, (payload, context) ->
                context.client().execute(() ->
                        context.client().setScreen(new ComputerScreen(
                                payload.pos(),
                                payload.title(),
                                payload.code(),
                                payload.locks()
                        ))
                )
        );
        ClientPlayNetworking.registerGlobalReceiver(OpenOutputNumberPayload.TYPE, (payload, context) ->
                context.client().execute(() ->
                        context.client().setScreen(new OutputNumberScreen(payload.pos(), payload.number()))
                )
        );
    }
}
