id SERIAL PRIMARY KEY,
       event_type VARCHAR(50),
       user_id VARCHAR(100),
       resource_id VARCHAR(100),
       action VARCHAR(50),
       timestamp TIMESTAMP,
       ip_address INET,
       user_agent TEXT,
       changes JSONB
   );