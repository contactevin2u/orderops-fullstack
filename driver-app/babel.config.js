// driver-app/babel.config.js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      ['module-resolver', { root: ['./'], alias: { '@': './src' } }],
      // Reanimated plugin MUST be last
      'react-native-reanimated/plugin',
    ],
  };
};
