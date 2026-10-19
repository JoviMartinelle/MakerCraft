package upx6.makercraft.computer;

import java.util.Locale;

public final class ComputerProgram {

    public static final int MAX_CHARS = 2000;
    public static final int MAX_LINES = 32;

    private ComputerProgram() {
    }

    public static String validate(String raw) {
        String text = raw == null ? "" : raw.replace("\r\n", "\n").replace('\r', '\n');
        if (text.length() > MAX_CHARS) {
            return "O programa passou de 2000 caracteres.";
        }

        String[] lines = text.split("\n", -1);
        if (lines.length > MAX_LINES) {
            return "O programa passou de 32 linhas.";
        }

        boolean insideWhen = false;
        boolean sawElse = false;

        for (int i = 0; i < lines.length; i++) {
            String line = lines[i].trim();
            int number = i + 1;
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }

            String[] parts = line.toLowerCase(Locale.ROOT).split("\\s+");
            String command = parts[0];

            switch (command) {
                case "ligar", "desligar" -> {
                    if (parts.length != 2 || !isNumber(parts[1], 1, 64)) {
                        return "Linha " + number + ": use ligar 1 ou desligar 1.";
                    }
                }
                case "esperar" -> {
                    if (parts.length != 2 || !isNumber(parts[1], 0, 60000)) {
                        return "Linha " + number + ": use esperar e os milissegundos, até 60000.";
                    }
                }
                case "led" -> {
                    if (parts.length != 2 || !(parts[1].equals("ligado") || parts[1].equals("desligado"))) {
                        return "Linha " + number + ": use led ligado ou led desligado.";
                    }
                }
                case "quando" -> {
                    if (parts.length != 2 || !parts[1].equals("sinal")) {
                        return "Linha " + number + ": use quando sinal.";
                    }
                    if (insideWhen) {
                        return "Linha " + number + ": não dá para aninhar quando.";
                    }
                    insideWhen = true;
                    sawElse = false;
                }
                case "senao" -> {
                    if (parts.length != 1 || !insideWhen || sawElse) {
                        return "Linha " + number + ": senao fora de lugar.";
                    }
                    sawElse = true;
                }
                case "fim" -> {
                    if (parts.length != 1 || !insideWhen) {
                        return "Linha " + number + ": fim fora de lugar.";
                    }
                    insideWhen = false;
                }
                case "repetir" -> {
                    if (parts.length != 1) {
                        return "Linha " + number + ": repetir não leva número.";
                    }
                    if (insideWhen) {
                        return "Linha " + number + ": repetir fica fora do quando.";
                    }
                }
                default -> {
                    return "Linha " + number + ": comando desconhecido.";
                }
            }
        }

        if (insideWhen) {
            return "Falta o fim do quando.";
        }

        return null;
    }

    public static String toProtocol(String raw) {
        String text = raw == null ? "" : raw.replace("\r\n", "\n").replace('\r', '\n');
        StringBuilder out = new StringBuilder("PROGRAM_BEGIN\n");
        for (String line : text.split("\n", -1)) {
            String trimmed = line.trim();
            if (trimmed.isEmpty()) {
                continue;
            }
            if (trimmed.startsWith("#")) {
                out.append(trimmed).append('\n');
            } else {
                out.append(trimmed.toLowerCase(Locale.ROOT)).append('\n');
            }
        }
        out.append("PROGRAM_END\n");
        return out.toString();
    }

    private static boolean isNumber(String text, int min, int max) {
        try {
            int value = Integer.parseInt(text);
            return value >= min && value <= max;
        } catch (NumberFormatException e) {
            return false;
        }
    }
}
