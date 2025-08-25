
import NextAuth, { NextAuthOptions } from 'next-auth';
import GitHubProvider from 'next-auth/providers/github';

export const authOptions: NextAuthOptions = {

    }),
  ],
  session: {
    strategy: 'jwt',
  },
};

export default NextAuth(authOptions);

