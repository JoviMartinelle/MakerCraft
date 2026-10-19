package upx6.makercraft.computer;

import java.util.ArrayList;
import java.util.List;

public final class ComputerLocks {

    private ComputerLocks() {
    }

    public static List<String> lines(String code) {
        String text = code == null ? "" : code.replace("\r\n", "\n").replace('\r', '\n');
        if (text.isEmpty()) {
            return List.of();
        }

        String[] parts = text.split("\n", -1);
        List<String> lines = new ArrayList<>(parts.length);
        for (String part : parts) {
            lines.add(part);
        }
        return lines;
    }

    public static boolean[] flags(List<String> lines, String mask) {
        boolean[] flags = new boolean[lines.size()];
        if (mask == null) {
            return flags;
        }

        int count = Math.min(lines.size(), mask.length());
        for (int i = 0; i < count; i++) {
            flags[i] = mask.charAt(i) == '1';
        }
        return flags;
    }

    public static String mask(boolean[] flags) {
        StringBuilder out = new StringBuilder(flags.length);
        for (boolean flag : flags) {
            out.append(flag ? '1' : '0');
        }
        return out.toString();
    }

    public static String fit(String code, String mask) {
        return mask(flags(lines(code), mask));
    }

    /**
     * @return the lock mask for the new text, or null when a locked line was removed or edited
     */
    public static String realign(String oldCode, String oldMask, String newCode, boolean strict) {
        List<String> oldLines = lines(oldCode);
        List<String> newLines = lines(newCode);
        boolean[] oldFlags = flags(oldLines, oldMask);

        if (!strict && oldLines.size() == newLines.size()) {
            return mask(oldFlags);
        }

        boolean[] next = new boolean[newLines.size()];
        int start = 0;
        for (int i = 0; i < oldLines.size(); i++) {
            if (!oldFlags[i]) {
                continue;
            }

            int found = -1;
            for (int j = start; j < newLines.size(); j++) {
                if (newLines.get(j).equals(oldLines.get(i))) {
                    found = j;
                    break;
                }
            }

            if (found < 0) {
                if (strict) {
                    return null;
                }
                continue;
            }

            next[found] = true;
            start = found + 1;
        }

        return mask(next);
    }
}
