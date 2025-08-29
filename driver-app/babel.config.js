module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      [
        'module-resolver',
        {
          root: ['./'],
          extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
          alias: {
            '@core': './src/core',
            '@infra': './src/infrastructure',
            '@presentation': './src/presentation',
            '@shared': './src/shared',
          },
        },
      ],
    ],
  };
};
