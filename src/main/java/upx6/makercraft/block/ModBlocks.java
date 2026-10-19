package upx6.makercraft.block;

import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import upx6.makercraft.MakerCraft;
import upx6.makercraft.block.ArduinoOutputBlock;

public class ModBlocks {

    public static final Block ARDUINO_BLOCK = register(
            "arduino_block",
            ArduinoBlock::new,
            BlockBehaviour.Properties.of()
    );

    public static final Block ARDUINO_OUTPUT_BLOCK = register(
            "arduino_output",
            ArduinoOutputBlock::new,
            BlockBehaviour.Properties.of()
    );

    public static final Block COMPUTER = register(
            "computer",
            ComputerBlock::new,
            BlockBehaviour.Properties.of().strength(1.5f)
    );

    private static Block register(
            String name,
            java.util.function.Function<BlockBehaviour.Properties, Block> factory,
            BlockBehaviour.Properties properties
    ) {
        ResourceKey<Block> key = ResourceKey.create(
                Registries.BLOCK,
                MakerCraft.id(name)
        );

        return Registry.register(
                BuiltInRegistries.BLOCK,
                key,
                factory.apply(properties.setId(key))
        );
    }

    public static void initialize() {
        MakerCraft.LOGGER.info("Registrando blocos do MakerCraft");
    }
}