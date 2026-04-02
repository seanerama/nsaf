import { execSync } from 'child_process';
import pino from 'pino';

const log = pino({ name: 'nsaf.postgres' });

export function createDatabase(slug, pgHost, pgPort, pgUser, pgPassword) {
  const dbName = `nsaf_${slug.replace(/-/g, '_')}`;

  try {
    execSync(
      `PGPASSWORD="${pgPassword}" createdb -h "${pgHost}" -p "${pgPort}" -U "${pgUser}" "${dbName}"`,
      { stdio: 'pipe' }
    );
    log.info({ dbName }, 'Created PostgreSQL database');
  } catch (err) {
    // Database may already exist
    if (err.stderr && err.stderr.toString().includes('already exists')) {
      log.info({ dbName }, 'Database already exists');
    } else {
      throw err;
    }
  }

  const connStr = `postgresql://${pgUser}:${pgPassword}@${pgHost}:${pgPort}/${dbName}`;
  return { dbName, connectionString: connStr };
}

export function dropDatabase(slug, pgHost, pgPort, pgUser, pgPassword) {
  const dbName = `nsaf_${slug.replace(/-/g, '_')}`;

  try {
    execSync(
      `PGPASSWORD="${pgPassword}" dropdb -h "${pgHost}" -p "${pgPort}" -U "${pgUser}" --if-exists "${dbName}"`,
      { stdio: 'pipe' }
    );
    log.info({ dbName }, 'Dropped PostgreSQL database');
  } catch (err) {
    log.error({ dbName, error: err.message }, 'Failed to drop database');
  }
}
