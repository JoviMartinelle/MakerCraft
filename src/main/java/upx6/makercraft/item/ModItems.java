package upx6.makercraft.item;

import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import upx6.makercraft.MakerCraft;
import upx6.makercraft.block.ModBlocks;

public class ModItems {

    public static final Item ARDUINO_BLOCK = register(
            "arduino_block",
            properties -> new BlockItem(ModBlocks.ARDUINO_BLOCK, properties),
            new Item.Properties()
    );

    public static final Item ARDUINO_OUTPUT = register(
            "arduino_output",
            properties -> new BlockItem(ModBlocks.ARDUINO_OUTPUT_BLOCK, properties),
            new Item.Properties()
    );

    private static Item register(
            String name,
            java.util.function.Function<Item.Properties, Item> factory,
            Item.Properties properties
    ) {
        ResourceKey<Item> key = ResourceKey.create(
                Registries.ITEM,
                MakerCraft.id(name)
        );

        return Registry.register(
                BuiltInRegistries.ITEM,
                key,
                factory.apply(properties.setId(key))
        );
    }

    public static void initialize() {
        MakerCraft.LOGGER.info("Registrando itens do MakerCraft");
    }
}