package upx6.makercraft.serial;

import com.fazecast.jSerialComm.SerialPort;

import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;

public class SerialManager {

    private static SerialPort connectedPort;

    // Buffer que acumula os pedaços recebidos pela porta serial
    private static final StringBuilder receiveBuffer =
            new StringBuilder();

    private static final Queue<String> outgoing =
            new ConcurrentLinkedQueue<>();

    public static SerialPort[] getAvailablePorts() {
        return SerialPort.getCommPorts();
    }

    /**
     * COM1 ("Communications Port") abre no Windows mesmo sem nada ligado,
     * e o writeBytes nativo trava para sempre. Só aceitamos adaptadores USB.
     */
    public static boolean looksLikeArduino(SerialPort port) {
        String description = port.getDescriptivePortName()
                .toLowerCase(Locale.ROOT);

        return description.contains("ch340")
                || description.contains("ch341")
                || description.contains("arduino")
                || description.contains("usb-serial")
                || description.contains("usb serial")
                || description.contains("cp210")
                || description.contains("ftdi")
                || description.contains("wch");
    }

    public static boolean connect(String portName) {

        SerialPort port = SerialPort.getCommPort(portName);

        port.setBaudRate(9600);
        port.setFlowControl(SerialPort.FLOW_CONTROL_DISABLED);
        port.setComPortTimeouts(
                SerialPort.TIMEOUT_READ_SEMI_BLOCKING
                        | SerialPort.TIMEOUT_WRITE_BLOCKING,
                50,
                300
        );

        if (!port.openPort()) {
            return false;
        }

        connectedPort = port;

        // Limpa qualquer lixo que tenha ficado de uma conexão anterior
        synchronized (receiveBuffer) {
            receiveBuffer.setLength(0);
        }

        return true;
    }

    public static void disconnect() {
        SerialPort port = connectedPort;
        connectedPort = null;
        outgoing.clear();
        synchronized (receiveBuffer) {
            receiveBuffer.setLength(0);
        }
        if (port != null && port.isOpen()) {
            port.closePort();
        }
    }

    public static boolean isConnected() {
        SerialPort port = connectedPort;
        return port != null && port.isOpen();
    }

    public static void queueMessage(String message) {
        if (message != null && !message.isEmpty()) {
            outgoing.add(message);
        }
    }

    public static void drainOutgoing() {
        String message;
        while ((message = outgoing.poll()) != null) {
            sendRaw(message);
        }
    }

    public static void sendTestMessage(String message) {
        sendRaw(message + "\n");
    }

    private static void sendRaw(String message) {
        SerialPort port = connectedPort;

        if (port == null || !port.isOpen() || message == null || message.isEmpty()) {
            return;
        }

        byte[] data = message.getBytes(StandardCharsets.UTF_8);

        try {
            port.writeBytes(data, data.length);
        } catch (RuntimeException ignored) {
            // Uma falha de escrita não pode derrubar a thread do jogo.
        }
    }

    public static String readMessage() {

        if (connectedPort == null
                || !connectedPort.isOpen()) {

            return null;
        }

        byte[] buffer =
                new byte[1024];

        int bytesRead =
                connectedPort.readBytes(
                        buffer,
                        buffer.length
                );

        synchronized (receiveBuffer) {

            if (bytesRead > 0) {
                receiveBuffer.append(
                        new String(
                                buffer,
                                0,
                                bytesRead,
                                StandardCharsets.UTF_8
                        )
                );
            }

            // Procura uma mensagem completa
            int newlineIndex =
                    receiveBuffer.indexOf("\n");

            if (newlineIndex == -1) {

                // Ainda não chegou a mensagem completa
                return null;
            }

            // Extrai somente até o \n
            String message =
                    receiveBuffer
                            .substring(
                                    0,
                                    newlineIndex
                            )
                            .trim();

            // Remove a mensagem já processada
            receiveBuffer.delete(
                    0,
                    newlineIndex + 1
            );

            if (message.isEmpty()) {
                return null;
            }

            return message;
        }
    }
}
