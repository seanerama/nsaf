import { execFileSync } from 'child_process';
import pino from 'pino';

const log = pino({ name: 'nsaf.postgres' });

export function createDatabase(slug, pgHost, pgPort, pgUser, pgPassword) {
  const dbName = `nsaf_${slug.replace(/[^a-z0-9_]/g, '_')}`;

  try {
    execFileSync('createdb', ['-h', pgHost, '-p', pgPort, '-U', pgUser, dbName], {
      stdio: 'pipe',
      env: { ...process.env, PGPASSWORD: pgPassword },
    });
    log.info({ dbName }, 'Created PostgreSQL database');
  } catch (err) {
    if (err.stderr && err.stderr.toString().includes('already exists')) {
      log.info({ dbName }, 'Database already exists');
    } else {
      throw err;
    }
  }

  const connStr = `postgresql://${pgUser}:${encodeURIComponent(pgPassword)}@${pgHost}:${pgPort}/${dbName}`;
  return { dbName, connectionString: connStr };
}

export function dropDatabase(slug, pgHost, pgPort, pgUser, pgPassword) {
  const dbName = `nsaf_${slug.replace(/[^a-z0-9_]/g, '_')}`;

  try {
    execFileSync('dropdb', ['-h', pgHost, '-p', pgPort, '-U', pgUser, '--if-exists', dbName], {
      stdio: 'pipe',
      env: { ...process.env, PGPASSWORD: pgPassword },
    });
    log.info({ dbName }, 'Dropped PostgreSQL database');
  } catch (err) {
    log.error({ dbName, error: err.message }, 'Failed to drop database');
  }
}
