package upx6.makercraft.client;

import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.MultiLineEditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.MouseButtonEvent;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import upx6.makercraft.computer.ComputerLocks;
import upx6.makercraft.network.SaveComputerPayload;

import java.util.List;

public class ComputerScreen extends Screen {

    private static final int PANEL_WIDTH = 292;
    private static final int PANEL_HEIGHT = 196;
    private static final int LINE_HEIGHT = 9;
    private static final int INNER_PADDING = 4;

    private final BlockPos pos;
    private final String titleText;
    private final String initialCode;

    private MultiLineEditBox editor;
    private int panelLeft;
    private int panelTop;
    private boolean[] locks = new boolean[0];
    private String acceptedText = "";
    private boolean applying;

    public ComputerScreen(BlockPos pos, String title, String code, String locks) {
        super(Component.literal(title == null || title.isBlank() ? "Computador" : title));
        this.pos = pos;
        this.titleText = title == null || title.isBlank() ? "Computador" : title;
        this.initialCode = code == null ? "" : code;
        this.acceptedText = this.initialCode;
        this.locks = ComputerLocks.flags(ComputerLocks.lines(this.initialCode), locks);
    }

    @Override
    protected void init() {
        panelLeft = (this.width - PANEL_WIDTH) / 2;
        panelTop = (this.height - PANEL_HEIGHT) / 2;

        editor = MultiLineEditBox.builder()
                .setX(panelLeft + 26)
                .setY(panelTop + 36)
                .setPlaceholder(Component.literal("ligar 1"))
                .setTextColor(0xFFE7FFF3)
                .setTextShadow(false)
                .setCursorColor(0xFF3DDC97)
                .setShowBackground(false)
                .setShowDecorations(false)
                .build(this.font, PANEL_WIDTH - 40, 112, Component.literal("código"));
        editor.setValue(initialCode);
        editor.setCharacterLimit(2000);
        editor.setLineLimit(32);
        editor.setValueListener(this::onTextChanged);
        addRenderableWidget(editor);

        addRenderableWidget(Button.builder(Component.literal("Executar"), button -> send(true))
                .bounds(panelLeft + PANEL_WIDTH - 92, panelTop + PANEL_HEIGHT - 28, 78, 20)
                .build());

        setInitialFocus(editor);
    }

    @Override
    public void renderBackground(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        super.renderBackground(graphics, mouseX, mouseY, partialTick);

        int right = panelLeft + PANEL_WIDTH;
        int bottom = panelTop + PANEL_HEIGHT;

        graphics.fill(panelLeft - 2, panelTop - 2, right + 2, bottom + 2, 0xFF0B0E0C);
        graphics.fill(panelLeft, panelTop, right, bottom, 0xFF171C19);
        graphics.fill(panelLeft, panelTop, right, panelTop + 3, 0xFF1FA87A);
        graphics.fill(panelLeft + 10, panelTop + 32, right - 10, panelTop + 152, 0xFF0C1210);
        graphics.fill(panelLeft + 10, panelTop + 32, right - 10, panelTop + 33, 0xFF1C3A30);
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        super.render(graphics, mouseX, mouseY, partialTick);

        graphics.drawString(this.font, this.titleText, panelLeft + 14, panelTop + 10, 0xFFF3FFF8, false);
        graphics.drawString(this.font, hint(), panelLeft + 14, panelTop + 20, 0xFF8FBFB0, false);
        graphics.drawString(this.font, lineLabel(), panelLeft + 14, panelTop + PANEL_HEIGHT - 22, 0xFFB7F5D8, false);
        drawLocks(graphics);
    }

    @Override
    public boolean mouseClicked(MouseButtonEvent event, boolean doubleClick) {
        if (event.button() == 0 && clickLock(event.x(), event.y())) {
            return true;
        }
        return super.mouseClicked(event, doubleClick);
    }

    @Override
    public void onClose() {
        send(false);
        super.onClose();
    }

    private void onTextChanged(String value) {
        if (applying || editor == null) {
            return;
        }

        String previous = acceptedText;
        boolean[] previousLocks = locks;
        String realigned = ComputerLocks.realign(previous, ComputerLocks.mask(previousLocks), value, !creative());
        if (realigned == null) {
            applying = true;
            editor.setValue(previous);
            applying = false;
            return;
        }

        acceptedText = value;
        locks = ComputerLocks.flags(ComputerLocks.lines(value), realigned);
    }

    private boolean clickLock(double mouseX, double mouseY) {
        int line = lineAt(mouseX, mouseY);
        if (line < 0) {
            return false;
        }

        if (!creative()) {
            if (line < locks.length && locks[line]) {
                if (this.minecraft != null && this.minecraft.player != null) {
                    this.minecraft.player.displayClientMessage(
                            Component.literal("Só o modo criativo destranca uma linha."),
                            true
                    );
                }
            }
            return line < locks.length && locks[line];
        }

        if (line >= locks.length) {
            return false;
        }

        locks[line] = !locks[line];
        return true;
    }

    private void drawLocks(GuiGraphics graphics) {
        if (editor == null) {
            return;
        }

        List<String> lines = ComputerLocks.lines(editor.getValue());
        int top = editor.getY() + INNER_PADDING;
        int bottom = editor.getY() + editor.getHeight() - INNER_PADDING;
        double scroll = editor.scrollAmount();

        for (int i = 0; i < lines.size() && i < locks.length; i++) {
            if (!creative() && !locks[i]) {
                continue;
            }

            int y = (int) (top + i * LINE_HEIGHT - scroll);
            if (y < top || y + 7 > bottom) {
                continue;
            }

            int x = panelLeft + 14;
            int border = locks[i] ? 0xFF1FA87A : 0xFF3C4A44;
            graphics.fill(x, y + 1, x + 7, y + 8, border);
            graphics.fill(x + 1, y + 2, x + 6, y + 7, locks[i] ? 0xFF14382C : 0xFF0C1210);
            if (locks[i]) {
                graphics.fill(x + 2, y + 4, x + 5, y + 7, 0xFFE7FFF3);
            }
        }
    }

    private int lineAt(double mouseX, double mouseY) {
        if (editor == null) {
            return -1;
        }

        int top = editor.getY() + INNER_PADDING;
        int bottom = editor.getY() + editor.getHeight() - INNER_PADDING;
        if (mouseX < panelLeft + 12 || mouseX > panelLeft + 24 || mouseY < top || mouseY >= bottom) {
            return -1;
        }

        int line = (int) Math.floor((mouseY - top + editor.scrollAmount()) / LINE_HEIGHT);
        List<String> lines = ComputerLocks.lines(editor.getValue());
        if (line < 0 || line >= lines.size()) {
            return -1;
        }
        return line;
    }

    private void send(boolean execute) {
        if (this.editor == null || this.minecraft == null) {
            return;
        }

        ClientPlayNetworking.send(new SaveComputerPayload(
                this.pos,
                this.editor.getValue(),
                ComputerLocks.mask(locks),
                execute
        ));
    }

    private boolean creative() {
        return this.minecraft != null
                && this.minecraft.player != null
                && this.minecraft.player.isCreative();
    }

    private String hint() {
        if (creative()) {
            return "Clique no quadrado para trancar a linha";
        }
        return "Linha com quadrado fechado é obrigatória";
    }

    private String lineLabel() {
        int lines = ComputerLocks.lines(editor == null ? "" : editor.getValue()).size();
        int locked = 0;
        for (boolean lock : locks) {
            if (lock) {
                locked++;
            }
        }

        String total = lines == 1 ? "1 linha" : lines + " linhas";
        if (locked == 0) {
            return total;
        }
        String lockedLabel = locked == 1 ? "1 trancada" : locked + " trancadas";
        return total + " · " + lockedLabel;
    }
}
