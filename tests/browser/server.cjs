'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '../..');
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'cnm-browser-release-'));
const output = path.join(temporary, 'site');
const version = process.env.GITHUB_SHA || 'a'.repeat(40);
const build = spawnSync('python3', ['scripts/build_site.py', '--version', version, '--output', output], {
  cwd: root, stdio: 'inherit'
});
if (build.status !== 0) {
  fs.rmSync(temporary, { recursive: true, force: true });
  process.exit(build.status || 1);
}

const serverCode = `
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import sys
class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *args):
        pass
class Server(ThreadingHTTPServer):
    request_queue_size = 128
Server(('127.0.0.1', int(sys.argv[1])), partial(Handler, directory=sys.argv[2])).serve_forever()
`;
const server = spawn('python3', ['-u', '-c', serverCode, process.env.PLAYWRIGHT_PORT || '8769', output], {
  cwd: root, stdio: 'inherit'
});
let shuttingDown = false;
function stop() {
  if (shuttingDown) return;
  shuttingDown = true;
  server.kill('SIGTERM');
}
process.on('SIGINT', stop);
process.on('SIGTERM', stop);
server.on('exit', code => {
  fs.rmSync(temporary, { recursive: true, force: true });
  process.exit(shuttingDown ? 0 : code || 0);
});
server.on('error', error => {
  console.error(error);
  fs.rmSync(temporary, { recursive: true, force: true });
  process.exitCode = 1;
});
