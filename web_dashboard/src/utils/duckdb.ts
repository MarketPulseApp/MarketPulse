import * as duckdb from '@duckdb/duckdb-wasm';
import duckdb_wasm from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url';
import mvp_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url';
import duckdb_wasm_eh from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url';
import eh_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url';

const MANUAL_BUNDLES: duckdb.DuckDBBundles = {
    mvp: {
        mainModule: duckdb_wasm,
        mainWorker: mvp_worker,
    },
    eh: {
        mainModule: duckdb_wasm_eh,
        mainWorker: eh_worker,
    },
};

let db: duckdb.AsyncDuckDB | null = null;

export async function getDb() {
    if (db) return db;
    
    const logger = new duckdb.ConsoleLogger();
    const worker = await duckdb.selectBundle(MANUAL_BUNDLES);
    const inst = new duckdb.AsyncDuckDB(logger, new Worker(worker.mainWorker!));
    await inst.instantiate(worker.mainModule, worker.pthreadWorker);
    
    db = inst;
    return db;
}
