package upx6.makercraft.block;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.level.storage.ValueOutput;

public class ComputerBlockEntity extends BlockEntity {

    private String code = "";
    private String locks = "";
    private String title = "Computador";

    public ComputerBlockEntity(BlockPos pos, BlockState state) {
        super(ModBlockEntities.COMPUTER, pos, state);
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code == null ? "" : code;
    }

    public String getLocks() {
        return locks;
    }

    public void setLocks(String locks) {
        this.locks = locks == null ? "" : locks;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title == null || title.isBlank() ? "Computador" : title;
    }

    @Override
    protected void saveAdditional(ValueOutput output) {
        super.saveAdditional(output);
        output.putString("Code", code);
        output.putString("Locks", locks);
        output.putString("Title", title);
    }

    @Override
    protected void loadAdditional(ValueInput input) {
        super.loadAdditional(input);
        code = input.getStringOr("Code", "");
        locks = input.getStringOr("Locks", "");
        title = input.getStringOr("Title", "Computador");
    }
}
