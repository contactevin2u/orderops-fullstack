module.exports = {
  root: true,
  overrides: [
    {
      files: ['src/core/**/*'],
      rules: {
        'no-restricted-imports': [
          'error',
          {
            patterns: ['@infra/*', '@presentation/*', '@shared/constants/*'],
          },
        ],
      },
    },
    {
      files: ['src/presentation/**/*'],
      rules: {
        'no-restricted-imports': [
          'error',
          {
            patterns: ['@infra/*', '@shared/constants/*'],
          },
        ],
      },
    },
    {
      files: ['src/infrastructure/**/*'],
      rules: {
        'no-restricted-imports': [
          'error',
          { patterns: ['@presentation/*'] },
        ],
      },
    },
  ],
};
