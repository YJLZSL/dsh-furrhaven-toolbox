/**
 * 构建环境兜底声明：打包部署可能不带 @types/node，
 * 插件只用 child_process.execFile + process 两个能力，这里做最小声明。
 */
declare module 'node:child_process' {
  export interface ExecFileOptions {
    cwd?: string
    timeout?: number
    windowsHide?: boolean
    maxBuffer?: number
  }
  export function execFile(
    file: string,
    args: string[],
    options: ExecFileOptions,
    callback: (error: Error | null, stdout: string, stderr: string) => void,
  ): void
}

declare const process: {
  cwd(): string
  platform: string
}

declare const __dirname: string

declare module 'node:fs' {
  export function readFileSync(path: string, encoding: 'utf8'): string
}

declare module 'node:path' {
  export function join(...parts: string[]): string
}

/** 打包部署可能不带 dsh-tools 的声明文件，做最小结构声明。 */
declare module '@deepseek-ai/dsh-tools' {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  export function defineTool(def: any): any
}
