const childProcess = require('node:child_process')

const originalExec = childProcess.exec

childProcess.exec = function patchedExec(command, options, callback) {
  let resolvedOptions = options
  let resolvedCallback = callback

  if (typeof resolvedOptions === 'function') {
    resolvedCallback = resolvedOptions
    resolvedOptions = undefined
  }

  if (process.platform === 'win32' && typeof command === 'string' && command.trim().toLowerCase() === 'net use') {
    const cb = typeof resolvedCallback === 'function' ? resolvedCallback : null
    process.nextTick(() => {
      cb?.(null, '', '')
    })
    return {
      pid: 0,
      killed: false,
      kill() {},
      on() { return this },
      once() { return this },
      stdout: null,
      stderr: null,
    }
  }

  return originalExec.call(this, command, resolvedOptions, resolvedCallback)
}
