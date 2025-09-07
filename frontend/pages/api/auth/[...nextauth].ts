import NextAuth from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'

export default NextAuth({
  providers: [
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        username: { label: 'Username', type: 'text' },
        password: { label: 'Password', type: 'password' }
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) {
          return null
        }

        try {
          // Call your backend auth endpoint
          const backendUrl = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'
          const response = await fetch(`${backendUrl}/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              username: credentials.username,
              password: credentials.password,
            }),
          })

          if (response.ok) {
            const data = await response.json()
            return {
              id: data.user.id,
              name: data.user.username,
              email: data.user.username,
              role: data.user.role,
              token: data.access_token
            }
          }
        } catch (error) {
          console.error('Auth error:', error)
        }

        return null
      }
    })
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.role = user.role
        token.accessToken = user.token
      }
      return token
    },
    async session({ session, token }) {
      session.user.role = token.role
      session.accessToken = token.accessToken
      return session
    }
  },
  pages: {
    signIn: '/login',
  },
  secret: process.env.NEXTAUTH_SECRET,
})