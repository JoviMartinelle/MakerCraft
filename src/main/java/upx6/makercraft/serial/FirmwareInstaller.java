package upx6.makercraft.serial;

import net.fabricmc.loader.api.FabricLoader;
import upx6.makercraft.MakerCraft;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.TimeUnit;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

public final class FirmwareInstaller {

    public static final String VERSION = "1";
    public static final String READY = "MAKERCRAFT_READY " + VERSION;

    private static final String[] BOARDS = {
            "arduino:avr:uno",
            "arduino:avr:nano:cpu=atmega328old",
            "arduino:avr:nano"
    };

    private FirmwareInstaller() {
    }

    public static boolean install(String portName) {
        try {
            Path root = FabricLoader.getInstance().getConfigDir().resolve("makercraft");
            Path cli = ensureCli(root);
            writeConfig(root);
            ensureCore(cli, root);
            Path sketch = extractSketch(root);
            for (String board : BOARDS) {
                MakerCraft.LOGGER.info("Gravando o Arduino na {} como {}.", portName, board);
                if (run(cli, root, 180, "compile", "--upload", "-p", portName, "-b", board, sketch.toString()) == 0) {
                    return true;
                }
            }
            MakerCraft.LOGGER.error("Nenhuma gravação funcionou na porta {}.", portName);
            return false;
        } catch (Exception exception) {
            MakerCraft.LOGGER.error("Falha ao gravar o Arduino.", exception);
            return false;
        }
    }

    private static Path ensureCli(Path root) throws IOException, InterruptedException {
        Path tools = root.resolve("toolchain");
        Files.createDirectories(tools);
        String fileName = windows() ? "arduino-cli.exe" : "arduino-cli";
        Path cli = tools.resolve(fileName);
        if (Files.isRegularFile(cli)) {
            return cli;
        }

        MakerCraft.LOGGER.info("Baixando o gravador do Arduino. Isso acontece uma vez por computador.");
        Path archive = tools.resolve(windows() ? "arduino-cli.zip" : "arduino-cli.tar.gz");
        download(cliUrl(), archive);
        if (windows()) {
            unzipCli(archive, cli);
        } else {
            int code = new ProcessBuilder("tar", "-xzf", archive.toString(), "-C", tools.toString())
                    .redirectErrorStream(true)
                    .start()
                    .waitFor();
            if (code != 0 || !Files.isRegularFile(cli)) {
                throw new IOException("Não foi possível extrair o gravador.");
            }
            cli.toFile().setExecutable(true);
        }
        return cli;
    }

    private static void ensureCore(Path cli, Path root) throws IOException, InterruptedException {
        Path avr = root.resolve("toolchain").resolve("data").resolve("packages").resolve("arduino").resolve("hardware").resolve("avr");
        if (Files.isDirectory(avr)) {
            return;
        }

        MakerCraft.LOGGER.info("Baixando o suporte da placa Arduino. Isso também acontece uma vez.");
        run(cli, root, 180, "core", "update-index");
        if (run(cli, root, 600, "core", "install", "arduino:avr") != 0) {
            throw new IOException("Não foi possível instalar o suporte da placa Arduino.");
        }
    }

    private static Path extractSketch(Path root) throws IOException {
        Path sketch = root.resolve("firmware").resolve("ComputadorMakerCraft");
        Files.createDirectories(sketch);
        Path ino = sketch.resolve("ComputadorMakerCraft.ino");
        try (InputStream input = FirmwareInstaller.class.getClassLoader().getResourceAsStream(
                "assets/makercraft/firmware/ComputadorMakerCraft/ComputadorMakerCraft.ino"
        )) {
            if (input == null) {
                throw new IOException("O sketch não está dentro do mod.");
            }
            Files.copy(input, ino, StandardCopyOption.REPLACE_EXISTING);
        }
        return sketch;
    }

    private static void writeConfig(Path root) throws IOException {
        Path tools = root.resolve("toolchain");
        Files.createDirectories(tools.resolve("data"));
        Files.createDirectories(tools.resolve("downloads"));
        Files.createDirectories(tools.resolve("user"));
        String yaml = """
                directories:
                  data: %s
                  downloads: %s
                  user: %s
                """.formatted(
                tools.resolve("data").toAbsolutePath().toString().replace('\\', '/'),
                tools.resolve("downloads").toAbsolutePath().toString().replace('\\', '/'),
                tools.resolve("user").toAbsolutePath().toString().replace('\\', '/')
        );
        Files.writeString(tools.resolve("arduino-cli.yaml"), yaml);
    }

    private static int run(Path cli, Path root, long timeoutSeconds, String... args) throws IOException, InterruptedException {
        List<String> command = new ArrayList<>();
        command.add(cli.toAbsolutePath().toString());
        command.add("--config-file");
        command.add(root.resolve("toolchain").resolve("arduino-cli.yaml").toAbsolutePath().toString());
        command.addAll(List.of(args));

        Process process = new ProcessBuilder(command)
                .redirectErrorStream(true)
                .start();
        StringBuilder output = new StringBuilder();
        Thread reader = new Thread(() -> {
            try (InputStream input = process.getInputStream()) {
                output.append(new String(input.readAllBytes()));
            } catch (IOException ignored) {
                // O processo foi encerrado pelo tempo limite.
            }
        });
        reader.setDaemon(true);
        reader.start();

        if (!process.waitFor(timeoutSeconds, TimeUnit.SECONDS)) {
            process.destroyForcibly();
            reader.join(1000);
            throw new IOException("O gravador passou de " + timeoutSeconds + " segundos.");
        }
        reader.join(5000);
        if (!output.isEmpty()) {
            MakerCraft.LOGGER.info("{}", output.toString().trim());
        }
        return process.exitValue();
    }

    private static void download(String url, Path destination) throws IOException {
        java.net.HttpURLConnection connection =
                (java.net.HttpURLConnection) URI.create(url).toURL().openConnection();
        connection.setConnectTimeout(20000);
        connection.setReadTimeout(180000);
        connection.setInstanceFollowRedirects(true);
        try (InputStream input = connection.getInputStream()) {
            Files.copy(input, destination, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    private static void unzipCli(Path archive, Path cli) throws IOException {
        try (ZipInputStream zip = new ZipInputStream(Files.newInputStream(archive))) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                String name = entry.getName().replace('\\', '/');
                if (name.endsWith("arduino-cli.exe") || name.endsWith("arduino-cli")) {
                    Files.copy(zip, cli, StandardCopyOption.REPLACE_EXISTING);
                    return;
                }
            }
        }
        throw new IOException("O arquivo baixado não contém o gravador.");
    }

    private static boolean windows() {
        return System.getProperty("os.name", "").toLowerCase(Locale.ROOT).contains("win");
    }

    private static String cliUrl() {
        String arch = System.getProperty("os.arch", "").toLowerCase(Locale.ROOT);
        boolean arm = arch.contains("aarch64") || arch.contains("arm");
        String os = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
        if (os.contains("win")) {
            return "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip";
        }
        if (os.contains("mac")) {
            return arm
                    ? "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_macOS_ARM64.tar.gz"
                    : "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_macOS_64bit.tar.gz";
        }
        return arm
                ? "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_ARM64.tar.gz"
                : "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_64bit.tar.gz";
    }
}
