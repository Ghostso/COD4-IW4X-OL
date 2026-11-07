import io, os

root = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1"

def edit(path, pairs):
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    for old, new in pairs:
        if text.count(old) != 1:
            raise SystemExit("anchor count=%d in %s for head:\n%r" % (text.count(old), path, old[:200]))
        text = text.replace(old, new)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("edited", path)

prog = os.path.join(root, "src", "Program.cs")

edit(prog, [
("using System.IO;\nusing System.Text;",
 "using System.Collections.Generic;\nusing System.IO;\nusing System.Text;"),
(
'''            string mode = "--run";
            string configPath = Path.Combine("config", "combat_server.cfg");
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "--selftest" || args[i] == "--run" || args[i] == "--print-protocol" ||
                    args[i] == "--print-session" || args[i] == "--export-session" ||
                    args[i] == "--fingerprint" ||
                    args[i] == "--help" || args[i] == "-h" || args[i] == "--version")
                    mode = args[i];
                else if (args[i] == "--config" && i + 1 < args.Length) configPath = args[++i];
            }''',
'''            string mode = "--run";
            string configPath = Path.Combine("config", "combat_server.cfg");
            double maxSeconds = 0.0;                       // >0 = --run 在 N 秒后自动退出（可重复验证）
            List<string> cfgArgs = new List<string>();     // 传给 ServerConfig.Load 的参数（已剔除 --max-seconds）
            for (int i = 0; i < args.Length; i++)
            {
                string a = args[i];
                if (a == "--selftest" || a == "--run" || a == "--print-protocol" ||
                    a == "--print-session" || a == "--export-session" ||
                    a == "--fingerprint" ||
                    a == "--help" || a == "-h" || a == "--version")
                {
                    mode = a;
                    cfgArgs.Add(a);
                }
                else if (a == "--config" && i + 1 < args.Length)
                {
                    configPath = args[++i];
                    cfgArgs.Add("--config");
                    cfgArgs.Add(configPath);
                }
                else if (a == "--max-seconds")
                {
                    if (i + 1 >= args.Length) return BadMaxSeconds(null);
                    if (!TryParseMaxSeconds(args[++i], out maxSeconds)) return BadMaxSeconds(args[i]);
                }
                else if (a.StartsWith("--max-seconds=", StringComparison.Ordinal))
                {
                    string raw = a.Substring("--max-seconds=".Length);
                    if (!TryParseMaxSeconds(raw, out maxSeconds)) return BadMaxSeconds(raw);
                }
                else
                {
                    cfgArgs.Add(a);
                }
            }'''
),
(
'''            ServerConfig cfg = ServerConfig.Load(configPath, args, log);
            log.Dispose();

            if (mode == "--selftest")
                return SelfTest.Run(cfg);

            return RunServer(cfg);''',
'''            ServerConfig cfg = ServerConfig.Load(configPath, cfgArgs.ToArray(), log);
            log.Dispose();

            if (mode == "--selftest")
                return SelfTest.Run(cfg);

            return RunServer(cfg, maxSeconds);'''
),
(
'''                "  --run              启动战斗服主循环（默认）",
                "  --selftest         运行离线协议自测（不需要游戏/客户端）",''',
'''                "  --run              启动战斗服主循环（默认）",
                "  --max-seconds <N>  --run 运行 N 秒后自动退出（可重复验证启动/运行/清理）",
                "  --selftest         运行离线协议自测（不需要游戏/客户端）",'''
),
(
'''        private static int RunServer(ServerConfig cfg)
        {
            ServerHost host = new ServerHost(cfg);
            if (!host.Initialize())
            {
                Console.Error.WriteLine("[FATAL] 初始化失败 phase=" + host.Phase + " : " + host.FailReason);
                host.Dispose();
                return 2;
            }
            Console.WriteLine("[*] 按 Ctrl+C 停止");
            Console.CancelKeyPress += delegate (object s, ConsoleCancelEventArgs e) { e.Cancel = true; host.RequestStop(); };
            try
            {
                host.Run();
            }
            finally
            {
                host.Dispose();
            }
            return 0;
        }''',
'''        /// <summary>--max-seconds 允许的最大值（7 天），防止把毫秒/纳秒误当秒。</summary>
        private const double MaxAutoSeconds = 7.0 * 24.0 * 3600.0;

        /// <summary>解析 --max-seconds：必须是 0 &lt; N &lt;= MaxAutoSeconds 的有限秒数。</summary>
        private static bool TryParseMaxSeconds(string raw, out double seconds)
        {
            seconds = 0.0;
            double v;
            if (raw == null) return false;
            if (!double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out v)) return false;
            if (v <= 0.0 || double.IsNaN(v) || double.IsInfinity(v) || v > MaxAutoSeconds) return false;
            seconds = v;
            return true;
        }

        private static int BadMaxSeconds(string raw)
        {
            Console.Error.WriteLine("[FATAL] --max-seconds 非法: '" + (raw ?? "(缺少参数)") +
                                    "' （要求 0 < N <= 604800 秒）");
            return 5;
        }

        private static int RunServer(ServerConfig cfg, double maxSeconds)
        {
            ServerHost host = new ServerHost(cfg);
            host.RunSecondsLimit = maxSeconds;
            if (!host.Initialize())
            {
                Console.Error.WriteLine("[FATAL] 初始化失败 phase=" + host.Phase + " : " + host.FailReason);
                host.Dispose();
                return 2;
            }
            if (maxSeconds > 0.0)
                Console.WriteLine("[*] 自动退出已启用: max-seconds=" +
                                  maxSeconds.ToString(CultureInfo.InvariantCulture) +
                                  "（运行 N 秒后自动停止，用于可重复验证启动/运行/清理）");
            Console.WriteLine("[*] 按 Ctrl+C 停止");
            Console.CancelKeyPress += delegate (object s, ConsoleCancelEventArgs e) { e.Cancel = true; host.RequestStop(); };
            try
            {
                host.Run();
            }
            finally
            {
                host.Dispose();
            }

            // 停机清理自检：会话表 / 权威实体表都必须归零，否则报告为失败（不静默）。
            int sessions = (host.Logic != null) ? host.Logic.SessionCount : -1;
            int entities = (host.World != null) ? host.World.EntityCount : -1;
            if (sessions == 0 && entities == 0)
            {
                Console.WriteLine("[*] 停机清理自检通过: sessions=0 entities=0");
                return 0;
            }
            Console.Error.WriteLine("[FAIL] 停机清理不完整: sessions=" + sessions + " entities=" + entities);
            return 6;
        }'''
),
])

host = os.path.join(root, "src", "Engine", "ServerHost.cs")

edit(host, [
("        /// <summary>测试用的时钟注入：非 null 时替代 SystemClock（离线自测用）。</summary>\n        public IClock ClockOverride;",
 "        /// <summary>测试用的时钟注入：非 null 时替代 SystemClock（离线自测用）。</summary>\n        public IClock ClockOverride;\n\n        /// <summary>--max-seconds：>0 时主循环运行 N 秒后自动 RequestStop（可重复验证启动/运行/清理）；0 = 不限。</summary>\n        public double RunSecondsLimit = 0.0;"),
(
'''            Stopwatch sw = Stopwatch.StartNew();

            while (!_stop)
            {
                double now = _clock.NowSeconds;''',
'''            Stopwatch sw = Stopwatch.StartNew();
            if (RunSecondsLimit > 0.0)
                _log.Info("BOOT", "自动退出已启用 max-seconds=" + RunSecondsLimit.ToString(CultureInfo.InvariantCulture));

            while (!_stop)
            {
                if (RunSecondsLimit > 0.0 && sw.Elapsed.TotalSeconds >= RunSecondsLimit)
                {
                    _log.Info("BOOT", "达到 max-seconds=" + RunSecondsLimit.ToString(CultureInfo.InvariantCulture) +
                                      " -> 请求停止（自动退出）");
                    _stop = true;
                    break;
                }

                double now = _clock.NowSeconds;'''
),
])

print("done")
