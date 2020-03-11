const webpack = require('webpack');
const CopyPlugin = require('copy-webpack-plugin');

const config = {
  devtool: 'eval-source-map',
  entry: __dirname + '/src/js/main.js',
  output:{
    path: __dirname + '/dist',
    filename: 'bundle.js',
    library: 'main',
    libraryTarget: 'window',
  },
  resolve: {
    extensions: ['.js', '.css']
  },
  plugins: [
    new webpack.ProvidePlugin({
      $: "jquery",
      jQuery: "jquery"
    }),
    new CopyPlugin([
      { from: 'src/presets', to: 'presets', test: /\.json$/ }
    ])
  ],
  module: {
    rules: [
      {
        test: /\.(scss)$/,
        use: [{
          loader: 'style-loader',
        }, {
          loader: 'css-loader',
        }, {
          loader: 'postcss-loader',
          options: {
            plugins: function () {
              return [
                require('precss'),
                require('autoprefixer')
              ];
            }
          }
        }, {
          loader: 'sass-loader'
        }]
      },
			{
        test: /\.(woff(2)?|ttf|eot|svg)(\?v=\d+\.\d+\.\d+)?$/,
        use: [
          {
            loader: 'file-loader',
            options: {
              name: '[name].[ext]',
              outputPath: 'fonts/',
							publicPath: 'static/fonts/'
            }
          }
        ]
      }
    ]
  }
};

module.exports = config;
