package upx6.makercraft.client;

import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import org.lwjgl.glfw.GLFW;
import upx6.makercraft.network.SetOutputNumberPayload;

public class OutputNumberScreen extends Screen {

    private static final int PANEL_WIDTH = 220;
    private static final int PANEL_HEIGHT = 112;

    private final BlockPos pos;
    private final int currentNumber;

    private EditBox field;
    private int panelLeft;
    private int panelTop;

    public OutputNumberScreen(BlockPos pos, int currentNumber) {
        super(Component.literal("Saída Arduino"));
        this.pos = pos;
        this.currentNumber = currentNumber;
    }

    @Override
    protected void init() {
        panelLeft = (this.width - PANEL_WIDTH) / 2;
        panelTop = (this.height - PANEL_HEIGHT) / 2;

        field = new EditBox(this.font, panelLeft + 14, panelTop + 48, PANEL_WIDTH - 28, 20, Component.literal("Número"));
        field.setMaxLength(2);
        field.setValue(Integer.toString(currentNumber));
        field.setFilter(OutputNumberScreen::digitsOnly);
        field.setTextColor(0xFFE7FFF3);
        field.setBordered(false);
        addRenderableWidget(field);

        addRenderableWidget(Button.builder(Component.literal("Salvar"), button -> save())
                .bounds(panelLeft + PANEL_WIDTH - 78, panelTop + PANEL_HEIGHT - 28, 64, 20)
                .build());

        setInitialFocus(field);
    }

    @Override
    public void renderBackground(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        super.renderBackground(graphics, mouseX, mouseY, partialTick);

        int right = panelLeft + PANEL_WIDTH;
        int bottom = panelTop + PANEL_HEIGHT;

        graphics.fill(panelLeft - 2, panelTop - 2, right + 2, bottom + 2, 0xFF0B0E0C);
        graphics.fill(panelLeft, panelTop, right, bottom, 0xFF171C19);
        graphics.fill(panelLeft, panelTop, right, panelTop + 3, 0xFF1FA87A);
        graphics.fill(panelLeft + 14, panelTop + 46, right - 14, panelTop + 68, 0xFF0C1210);
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        super.render(graphics, mouseX, mouseY, partialTick);
        graphics.drawString(this.font, "Saída Arduino", panelLeft + 14, panelTop + 12, 0xFFF3FFF8, false);
        graphics.drawString(this.font, "Número do ligar e desligar", panelLeft + 14, panelTop + 24, 0xFF8FBFB0, false);
    }

    @Override
    public boolean keyPressed(KeyEvent event) {
        if (event.key() == GLFW.GLFW_KEY_ENTER || event.key() == GLFW.GLFW_KEY_KP_ENTER) {
            save();
            return true;
        }
        return super.keyPressed(event);
    }

    private void save() {
        if (this.field == null || this.minecraft == null) {
            return;
        }

        int number;
        try {
            number = Integer.parseInt(this.field.getValue());
        } catch (NumberFormatException exception) {
            return;
        }

        if (number < 1 || number > 64) {
            return;
        }

        ClientPlayNetworking.send(new SetOutputNumberPayload(this.pos, number));
        this.minecraft.setScreen(null);
    }

    private static boolean digitsOnly(String text) {
        if (text.isEmpty()) {
            return true;
        }
        if (text.length() > 2) {
            return false;
        }
        for (int i = 0; i < text.length(); i++) {
            if (!Character.isDigit(text.charAt(i))) {
                return false;
            }
        }
        return Integer.parseInt(text) <= 64;
    }
}
