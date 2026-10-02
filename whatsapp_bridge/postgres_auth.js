const { Pool } = require('pg');
const { proto, initAuthCreds, BufferJSON } = require('@whiskeysockets/baileys');

async function usePostgresAuthState(databaseUrl) {
  const pool = new Pool({
    connectionString: databaseUrl,
    ssl: { rejectUnauthorized: false }
  });

  // Ensure table exists
  await pool.query(`
    CREATE TABLE IF NOT EXISTS whatsapp_session (
      id VARCHAR(255) PRIMARY KEY,
      data TEXT NOT NULL,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
  `);

  const writeData = async (data, id) => {
    const serialized = JSON.stringify(data, BufferJSON.replacer);
    await pool.query(
      `INSERT INTO whatsapp_session (id, data, updated_at) VALUES ($1, $2, NOW())
       ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()`,
      [id, serialized]
    );
  };

  const readData = async (id) => {
    try {
      const res = await pool.query(`SELECT data FROM whatsapp_session WHERE id = $1`, [id]);
      if (res.rows.length === 0) return null;
      return JSON.parse(res.rows[0].data, BufferJSON.reviver);
    } catch (err) {
      return null;
    }
  };

  const removeData = async (id) => {
    try {
      await pool.query(`DELETE FROM whatsapp_session WHERE id = $1`, [id]);
    } catch (err) {}
  };

  const creds = (await readData('creds')) || initAuthCreds();

  return {
    state: {
      creds,
      keys: {
        get: async (type, ids) => {
          const data = {};
          await Promise.all(
            ids.map(async (id) => {
              let value = await readData(`${type}-${id}`);
              if (type === 'app-state-sync-key' && value) {
                value = proto.Message.AppStateSyncKeyData.fromObject(value);
              }
              data[id] = value;
            })
          );
          return data;
        },
        set: async (data) => {
          const tasks = [];
          for (const category in data) {
            for (const id in data[category]) {
              const value = data[category][id];
              const name = `${category}-${id}`;
              tasks.push(value ? writeData(value, name) : removeData(name));
            }
          }
          await Promise.all(tasks);
        }
      }
    },
    saveCreds: () => writeData(creds, 'creds')
  };
}

module.exports = { usePostgresAuthState };
