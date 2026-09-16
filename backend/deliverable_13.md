├── n8n Primary Instance (auto-scaling: 2-10 instances)
    ├── PostgreSQL RDS (Multi-AZ)
    └── Redis Cache (ElastiCache)

Failover Region (us-west-2)
    └── n8n Standby Instance (minimal footprint)