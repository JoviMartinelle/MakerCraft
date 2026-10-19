package upx6.makercraft.block;

import net.fabricmc.fabric.api.object.builder.v1.block.entity.FabricBlockEntityTypeBuilder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.block.entity.BlockEntityType;
import upx6.makercraft.MakerCraft;

public class ModBlockEntities {

    public static final BlockEntityType<ComputerBlockEntity> COMPUTER = Registry.register(
            BuiltInRegistries.BLOCK_ENTITY_TYPE,
            ResourceKey.create(Registries.BLOCK_ENTITY_TYPE, MakerCraft.id("computer")),
            FabricBlockEntityTypeBuilder.create(ComputerBlockEntity::new, ModBlocks.COMPUTER).build()
    );

    public static void initialize() {
        MakerCraft.LOGGER.info("Registrando block entities do MakerCraft");
    }
}
