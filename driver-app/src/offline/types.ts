export type OutboxJob = {
  id: string;
  createdAt: number;
  attempts: number;
  kind: 'PATCH' | 'UPLOAD' | 'POST' | 'DELETE';
  url: string;
  headers?: Record<string, string>;
  bodyType: 'json' | 'formdata' | 'none';
  body?: any;
};

