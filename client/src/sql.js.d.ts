declare module "sql.js" {
  interface SqlJsStatic {
    Database: typeof Database;
  }

  class Database {
    constructor(data?: ArrayLike<number>);
    run(sql: string, params?: unknown[]): Database;
    exec(sql: string, params?: unknown[]): { columns: string[]; values: unknown[][] }[];
    prepare(sql: string): Statement;
    export(): Uint8Array;
    close(): void;
  }

  class Statement {
    bind(params?: unknown[] | Record<string, unknown>): boolean;
    step(): boolean;
    getAsObject(): Record<string, unknown>;
    free(): boolean;
  }

  interface SqlJsConfig {
    wasmBinary?: Buffer;
    locateFile?: (file: string) => string;
  }

  export default function initSqlJs(config?: SqlJsConfig): Promise<SqlJsStatic>;
  export { Database };
}
