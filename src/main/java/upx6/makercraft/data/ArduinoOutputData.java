package upx6.makercraft.data;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.saveddata.SavedData;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;


public class ArduinoOutputData extends SavedData {

    // ==========================================================
    // LISTA DE OUTPUTS
    // ==========================================================

    private final List<OutputEntry> outputs;


    // ==========================================================
    // CONSTRUTOR
    // ==========================================================

    public ArduinoOutputData() {

        this.outputs =
                new ArrayList<>();
    }


    private ArduinoOutputData(
            List<OutputEntry> outputs
    ) {

        this.outputs =
                new ArrayList<>(outputs);

        // ======================================================
        // COMPATIBILIDADE COM SAVED DATA ANTIGO
        //
        // Caso existam Outputs antigos sem número,
        // atribuímos números automaticamente.
        // ======================================================

        assignMissingNumbers();
    }


    // ==========================================================
    // OUTPUT ENTRY
    // ==========================================================

    public static class OutputEntry {

        private final UUID id;

        private final int number;

        private final int x;
        private final int y;
        private final int z;

        private final String dimension;


        public OutputEntry(
                UUID id,
                int number,
                int x,
                int y,
                int z,
                String dimension
        ) {

            this.id = id;

            this.number = number;

            this.x = x;
            this.y = y;
            this.z = z;

            this.dimension = dimension;
        }


        public UUID getId() {
            return id;
        }


        public int getNumber() {
            return number;
        }


        public int getX() {
            return x;
        }


        public int getY() {
            return y;
        }


        public int getZ() {
            return z;
        }


        public String getDimension() {
            return dimension;
        }


        public BlockPos getBlockPos() {

            return new BlockPos(
                    x,
                    y,
                    z
            );
        }
    }


    // ==========================================================
    // CODEC DO OUTPUT ENTRY
    // ==========================================================

    private static final Codec<OutputEntry>
            OUTPUT_ENTRY_CODEC =
            RecordCodecBuilder.create(
                    instance ->
                            instance.group(

                                    Codec.STRING
                                            .fieldOf("Id")
                                            .forGetter(
                                                    entry ->
                                                            entry.getId()
                                                                    .toString()
                                            ),

                                    Codec.INT
                                            .optionalFieldOf(
                                                    "Number",
                                                    0
                                            )
                                            .forGetter(
                                                    OutputEntry::getNumber
                                            ),

                                    Codec.INT
                                            .fieldOf("X")
                                            .forGetter(
                                                    OutputEntry::getX
                                            ),

                                    Codec.INT
                                            .fieldOf("Y")
                                            .forGetter(
                                                    OutputEntry::getY
                                            ),

                                    Codec.INT
                                            .fieldOf("Z")
                                            .forGetter(
                                                    OutputEntry::getZ
                                            ),

                                    Codec.STRING
                                            .fieldOf("Dimension")
                                            .forGetter(
                                                    OutputEntry::getDimension
                                            )

                            ).apply(
                                    instance,
                                    (
                                            id,
                                            number,
                                            x,
                                            y,
                                            z,
                                            dimension
                                    ) -> new OutputEntry(
                                            UUID.fromString(id),
                                            number,
                                            x,
                                            y,
                                            z,
                                            dimension
                                    )
                            )
            );


    // ==========================================================
    // CODEC DO SAVED DATA
    // ==========================================================

    public static final Codec<ArduinoOutputData>
            CODEC =
            RecordCodecBuilder.create(
                    instance ->
                            instance.group(

                                    OUTPUT_ENTRY_CODEC
                                            .listOf()
                                            .fieldOf("Outputs")
                                            .forGetter(
                                                    data ->
                                                            data.outputs
                                            )

                            ).apply(
                                    instance,
                                    ArduinoOutputData::new
                            )
            );


    // ==========================================================
    // ENCONTRA O MENOR NÚMERO DISPONÍVEL
    // ==========================================================

    public int getNextOutputNumber() {

        int number = 1;


        while (hasOutputNumber(number)) {

            number++;
        }


        return number;
    }


    // ==========================================================
    // VERIFICA SE UM NÚMERO JÁ ESTÁ SENDO USADO
    // ==========================================================

    private boolean hasOutputNumber(
            int number
    ) {

        for (
                OutputEntry output :
                outputs
        ) {

            if (output.getNumber() == number) {

                return true;
            }
        }


        return false;
    }


    // ==========================================================
    // CORRIGE OUTPUTS ANTIGOS SEM NÚMERO
    // ==========================================================

    private void assignMissingNumbers() {

        boolean changed = false;


        for (int i = 0;
             i < outputs.size();
             i++) {

            OutputEntry output =
                    outputs.get(i);


            if (output.getNumber() > 0) {
                continue;
            }


            int newNumber =
                    getNextOutputNumber();


            OutputEntry corrected =
                    new OutputEntry(
                            output.getId(),
                            newNumber,
                            output.getX(),
                            output.getY(),
                            output.getZ(),
                            output.getDimension()
                    );


            outputs.set(
                    i,
                    corrected
            );


            changed = true;
        }


        if (changed) {

            setDirty();
        }
    }


    // ==========================================================
    // ADICIONAR OUTPUT
    // ==========================================================

    public void setOutput(
            UUID id,
            int x,
            int y,
            int z,
            String dimension
    ) {

        // ======================================================
        // SEGURANÇA:
        // NÃO PERMITE DUPLICATA NA MESMA POSIÇÃO
        // ======================================================

        OutputEntry existing =
                findOutputAt(
                        x,
                        y,
                        z,
                        dimension
                );


        if (existing != null) {

            return;
        }


        // ======================================================
        // PEGA O PRÓXIMO NÚMERO DISPONÍVEL
        // ======================================================

        int number =
                getNextOutputNumber();


        // ======================================================
        // ADICIONA
        // ======================================================

        outputs.add(
                new OutputEntry(
                        id,
                        number,
                        x,
                        y,
                        z,
                        dimension
                )
        );


        setDirty();
    }


    // ==========================================================
    // PROCURA OUTPUT PELA UUID
    // ==========================================================

    public OutputEntry findOutput(
            UUID id
    ) {

        for (
                OutputEntry output :
                outputs
        ) {

            if (output.getId()
                    .equals(id)) {

                return output;
            }
        }


        return null;
    }


    // ==========================================================
    // PROCURA OUTPUT PELO NÚMERO
    // ==========================================================

    public OutputEntry findOutputByNumber(
            int number
    ) {

        for (
                OutputEntry output :
                outputs
        ) {

            if (output.getNumber()
                    == number) {

                return output;
            }
        }


        return null;
    }


    // ==========================================================
    // PROCURA OUTPUT PELA POSIÇÃO
    // ==========================================================

    public OutputEntry findOutputAt(
            int x,
            int y,
            int z,
            String dimension
    ) {

        for (
                OutputEntry output :
                outputs
        ) {

            if (output.getX() == x
                    && output.getY() == y
                    && output.getZ() == z
                    && output.getDimension()
                    .equals(dimension)) {

                return output;
            }
        }


        return null;
    }


    // ==========================================================
    // RECUPERA BLOCK POS PELA UUID
    // ==========================================================

    public BlockPos getBlockPos(
            UUID id
    ) {

        OutputEntry output =
                findOutput(id);


        if (output == null) {

            return null;
        }


        return output.getBlockPos();
    }


    // ==========================================================
    // REMOVE OUTPUT PELA POSIÇÃO
    // ==========================================================

    public void removeOutputAt(
            int x,
            int y,
            int z,
            String dimension
    ) {

        outputs.removeIf(
                output ->
                        output.getX() == x
                                && output.getY() == y
                                && output.getZ() == z
                                && output.getDimension()
                                .equals(dimension)
        );


        setDirty();
    }


    // ==========================================================
    // GETTERS
    // ==========================================================

    public List<OutputEntry> getOutputs() {

        return new ArrayList<>(
                outputs
        );
    }


    public int getOutputCount() {

        return outputs.size();
    }
}

