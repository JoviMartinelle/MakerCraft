package upx6.makercraft.serial;

import com.fazecast.jSerialComm.SerialPort;

import java.nio.charset.StandardCharsets;

public class SerialManager {

    private static SerialPort connectedPort;

    // Buffer que acumula os pedaços recebidos pela porta serial
    private static final StringBuilder receiveBuffer =
            new StringBuilder();

    public static SerialPort[] getAvailablePorts() {
        return SerialPort.getCommPorts();
    }

    public static boolean connect(String portName) {

        connectedPort =
                SerialPort.getCommPort(portName);

        connectedPort.setBaudRate(9600);

        connectedPort.setComPortTimeouts(
                SerialPort.TIMEOUT_NONBLOCKING,
                0,
                0
        );

        if (!connectedPort.openPort()) {

            connectedPort = null;

            return false;
        }

        // Limpa qualquer lixo que tenha ficado de uma conexão anterior
        synchronized (receiveBuffer) {
            receiveBuffer.setLength(0);
        }

        return true;
    }

    public static void sendTestMessage(String message) {

        if (connectedPort == null
                || !connectedPort.isOpen()) {

            return;
        }

        byte[] data =
                (message + "\n")
                        .getBytes(StandardCharsets.UTF_8);

        connectedPort.writeBytes(
                data,
                data.length
        );
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

        if (bytesRead <= 0) {
            return null;
        }

        String received =
                new String(
                        buffer,
                        0,
                        bytesRead,
                        StandardCharsets.UTF_8
                );

        synchronized (receiveBuffer) {

            receiveBuffer.append(received);

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
