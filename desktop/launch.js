const { spawn } = require('child_process');
const electronPath = require('electron');
const env = Object.fromEntries(
  Object.entries(process.env).filter(([k]) => k !== 'ELECTRON_RUN_AS_NODE')
);
spawn(electronPath, ['.'], { stdio: 'inherit', env, detached: true }).unref();
setTimeout(() => process.exit(0), 2000);
