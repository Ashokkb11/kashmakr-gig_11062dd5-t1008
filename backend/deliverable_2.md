2. Slack Events API sends event to n8n webhook
3. n8n validates event signature and authenticity
4. Message content parsed for lead attributes
5. External enrichment (Clearbit/FullContact) [OPTIONAL]
6. Salesforce duplicate check performed
7. Lead record created/updated in Salesforce
8. Confirmation posted back to Slack thread
9. Audit log entry created
10. Metrics updated for monitoring