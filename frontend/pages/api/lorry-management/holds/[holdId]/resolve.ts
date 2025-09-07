import { NextApiRequest, NextApiResponse } from 'next';
import { getBackendUrl } from '../../../../../lib/api';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'PATCH') {
    try {
      const { holdId } = req.query;
      
      const response = await fetch(`${getBackendUrl()}/lorry-management/holds/${holdId}/resolve`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(req.body),
      });

      if (!response.ok) {
        const errorData = await response.json();
        return res.status(response.status).json(errorData);
      }

      const data = await response.json();
      res.status(200).json(data);
    } catch (error) {
      console.error('Error resolving driver hold:', error);
      res.status(500).json({ error: 'Failed to resolve driver hold' });
    }
  } else {
    res.setHeader('Allow', ['PATCH']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}