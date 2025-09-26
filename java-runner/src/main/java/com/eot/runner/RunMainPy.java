package com.eot.runner;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import static java.util.stream.Collectors.joining;

public final class RunMainPy {

  public static final class Result {
    public final int exitCode;
    public final String stdout;
    public final String stderr;
    public Result(int exitCode, String stdout, String stderr) {
      this.exitCode = exitCode; this.stdout = stdout; this.stderr = stderr;
    }
    @Override public String toString() {
      return "exitCode=" + exitCode + "\n--- STDOUT ---\n" + stdout + "\n--- STDERR ---\n" + stderr;
    }
  }

  /** Try .venv first; else fall back to python3/python.exe on PATH. */
  public static Path findPython(Path repoRoot) {
    Path venvUnix = repoRoot.resolve(".venv").resolve("bin").resolve("python");
    Path venvWin  = repoRoot.resolve(".venv").resolve("Scripts").resolve("python.exe");
    if (Files.isRegularFile(venvUnix)) return venvUnix;
    if (Files.isRegularFile(venvWin))  return venvWin;
    String os = System.getProperty("os.name").toLowerCase(Locale.ROOT);
    return Paths.get(os.contains("win") ? "python.exe" : "python3");
  }

  /** Walk up from start until we see tests/Main.py (max 5 levels). */
  public static Path autoDetectRepoRoot(Path start) throws IOException {
    Path p = start.toAbsolutePath().normalize();
    for (int i = 0; i < 5 && p != null; i++, p = p.getParent()) {
      if (Files.isRegularFile(p.resolve("tests").resolve("Main.py"))) return p;
    }
    throw new FileNotFoundException("Could not locate repo root containing tests/Main.py (start=" + start + ")");
  }

  /** Join parts into a PATH-like list using the OS list separator. */
  private static String joinOsPaths(String... parts) {
    String sep = File.pathSeparator; // ":" on *nix, ";" on Windows
    return Arrays.stream(parts).filter(s -> s != null && !s.isBlank()).collect(joining(sep));
  }

  /** Reads an InputStream line-by-line, echoes to console, and captures to a buffer. */
  private static final class StreamGobbler implements Callable<String> {
    private final InputStream in;
    private final PrintStream out;
    private final String prefix;
    StreamGobbler(InputStream in, PrintStream out, String prefix) {
      this.in = in; this.out = out; this.prefix = prefix;
    }
    @Override public String call() throws IOException {
      StringBuilder buf = new StringBuilder();
      try (BufferedReader br = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
        String line;
        while ((line = br.readLine()) != null) {
          out.println(prefix + line);  // realtime echo
          buf.append(line).append(System.lineSeparator());
        }
      }
      return buf.toString();
    }
  }

  /** Core runner. Streams logs live and enforces a timeout. */
  public static Result runMainPy(
      Path repoRoot,
      Path pythonExe,
      List<String> mainArgs,
      Map<String,String> extraEnv,
      long timeoutSeconds
  ) throws Exception {
    Path testsDir   = repoRoot.resolve("tests");
    Path mainScript = testsDir.resolve("Main.py");
    if (!Files.isRegularFile(mainScript)) {
      throw new FileNotFoundException("Main.py not found at: " + mainScript);
    }

    List<String> cmd = new ArrayList<>();
    cmd.add(pythonExe.toString());
    cmd.add("-u"); // force unbuffered io for realtime logs
    cmd.add(mainScript.toString());
    cmd.addAll(mainArgs);

    ProcessBuilder pb = new ProcessBuilder(cmd).directory(repoRoot.toFile());
    Map<String,String> env = pb.environment();
    env.put("PYTHONUNBUFFERED", "1");  // belt-and-suspenders with -u
    env.put("PYTHONPATH", joinOsPaths(
        repoRoot.toString(),
        testsDir.toString(),
        env.getOrDefault("PYTHONPATH", "")
    ));
    if (extraEnv != null) env.putAll(extraEnv);

    Process p = pb.start();

    ExecutorService es = Executors.newFixedThreadPool(2);
    Future<String> outF = es.submit(new StreamGobbler(p.getInputStream(), System.out,  "[py] "));
    Future<String> errF = es.submit(new StreamGobbler(p.getErrorStream(), System.err, "[py!] "));

    boolean finished = p.waitFor(timeoutSeconds, TimeUnit.SECONDS);
    if (!finished) {
      p.destroyForcibly();
      es.shutdownNow();
      throw new RuntimeException("Python process timed out after " + timeoutSeconds + "s");
    }

    String stdout = safeGet(outF);
    String stderr = safeGet(errF);
    es.shutdown();

    return new Result(p.exitValue(), stdout, stderr);
  }

  private static String safeGet(Future<String> f) throws Exception {
    try { return f.get(5, TimeUnit.SECONDS); }
    catch (TimeoutException te) { return ""; }
  }

  /** CLI entry for Gradle/Maven exec:java */
  public static void main(String[] args) throws Exception {
    String repoRootProp = System.getProperty("repoRoot");
    Path repoRoot = (repoRootProp == null || repoRootProp.isBlank())
        ? autoDetectRepoRoot(Paths.get("").toAbsolutePath())
        : Paths.get(repoRootProp).toAbsolutePath().normalize();

    Path pythonExe = findPython(repoRoot);

    String configProp = System.getProperty("config");
    Path cfg = (configProp == null || configProp.isBlank())
        ? repoRoot.resolve("config/Config.json")
        : Paths.get(configProp).toAbsolutePath().normalize();

    String dataProp = System.getProperty("data");
    Path data = (dataProp == null || dataProp.isBlank())
        ? repoRoot.resolve("config/TestData.csv")
        : Paths.get(dataProp).toAbsolutePath().normalize();

    long timeout = Long.parseLong(System.getProperty("timeoutSec", "900"));
    boolean verbose = Boolean.parseBoolean(System.getProperty("verbose", "true"));
    boolean dryRun  = Boolean.parseBoolean(System.getProperty("dryRun", "false"));

    List<String> mainArgs = new ArrayList<>();
    mainArgs.addAll(List.of("--config", cfg.toString(), "--data", data.toString()));
    if (verbose) mainArgs.add("-v");
    if (dryRun)  mainArgs.add("--dry-run");

    Result r = runMainPy(repoRoot, pythonExe, mainArgs, Map.of(), timeout);
    // At this point, logs were already printed live. We still print a summary:
    System.out.println("\n================ PYTHON RESULT ================\n" + r);
    if (r.exitCode != 0) {
      throw new IllegalStateException("Main.py failed with exit code " + r.exitCode);
    }
  }
}
