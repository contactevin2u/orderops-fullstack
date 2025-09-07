import { NextApiRequest, NextApiResponse } from 'next';
import { getBackendUrl } from '../../../lib/api';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'GET') {
    try {
      const { date } = req.query;
      const url = new URL(`${getBackendUrl()}/lorry-management/assignments`);
      if (date) {
        url.searchParams.set('date', date as string);
      }

      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Backend responded with ${response.status}`);
      }

      const data = await response.json();
      res.status(200).json(data);
    } catch (error) {
      console.error('Error fetching lorry assignments:', error);
      res.status(500).json({ error: 'Failed to fetch lorry assignments' });
    }
  } else if (req.method === 'POST') {
    try {
      const response = await fetch(`${getBackendUrl()}/lorry-management/assignments`, {
        method: 'POST',
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
      console.error('Error creating lorry assignment:', error);
      res.status(500).json({ error: 'Failed to create lorry assignment' });
    }
  } else {
    res.setHeader('Allow', ['GET', 'POST']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}