 package upx6.makercraft.data;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedDataType;

public class ModSavedData {

    public static final SavedDataType<ArduinoOutputData>
            ARDUINO_OUTPUT_DATA_TYPE =
            new SavedDataType<>(
                    "makercraft_arduino_output",
                    ArduinoOutputData::new,
                    ArduinoOutputData.CODEC,
                    null
            );

    public static ArduinoOutputData get(ServerLevel level) {

        return level.getDataStorage().computeIfAbsent(
                ARDUINO_OUTPUT_DATA_TYPE
        );
    }
}
