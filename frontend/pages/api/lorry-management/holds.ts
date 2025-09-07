import { NextApiRequest, NextApiResponse } from 'next';
import { getBackendUrl } from '../../../lib/api';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'GET') {
    try {
      const { driver_id } = req.query;
      const url = new URL(`${getBackendUrl()}/lorry-management/holds`);
      if (driver_id) {
        url.searchParams.set('driver_id', driver_id as string);
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
      console.error('Error fetching driver holds:', error);
      res.status(500).json({ error: 'Failed to fetch driver holds' });
    }
  } else if (req.method === 'POST') {
    try {
      const response = await fetch(`${getBackendUrl()}/lorry-management/holds`, {
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
      console.error('Error creating driver hold:', error);
      res.status(500).json({ error: 'Failed to create driver hold' });
    }
  } else {
    res.setHeader('Allow', ['GET', 'POST']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}