/**
 * PM2 ecosystem — IMP-04
 * 사용: 저장소 루트에서 `pm2 start deploy/ecosystem.config.cjs`
 * cwd / interpreter 경로는 호스트에 맞게 수정하세요.
 */
const path = require("path");
const root = path.resolve(__dirname, "..");

module.exports = {
  apps: [
    {
      name: "novel-agent",
      cwd: root,
      script: path.join(root, ".venv", "bin", "python"),
      // Windows: ".venv\\Scripts\\python.exe"
      args: "-m uvicorn app.main:app --host 127.0.0.1 --port 8080",
      interpreter: "none",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      max_memory_restart: "800M",
      env: {
        ENVIRONMENT: "production",
        // 시크릿은 여기에 하드코딩하지 말고 셸/.env 또는 env_file 로 주입
      },
      // PM2 2.5+: env_file 지원 시
      // env_file: path.join(root, ".env"),
      error_file: path.join(root, "deploy", "logs", "pm2-error.log"),
      out_file: path.join(root, "deploy", "logs", "pm2-out.log"),
      merge_logs: true,
      time: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
    },
  ],
};
