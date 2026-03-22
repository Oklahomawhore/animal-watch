#!/usr/bin/env node
/**
 * 林麝监测小程序 CI 上传脚本
 * 用于将小程序代码上传到微信后台
 */

const ci = require('miniprogram-ci');
const path = require('path');
const fs = require('fs');

// 小程序配置
const CONFIG = {
  // 小程序 AppID - 需要替换为实际值
  appid: process.env.WECHAT_APPID || 'wx YOUR_APPID_HERE',
  
  // 上传密钥文件路径 - 需要从微信小程序后台下载
  privateKeyPath: process.env.WECHAT_PRIVATE_KEY_PATH || './private.key',
  
  // 项目路径
  projectPath: path.resolve(__dirname, '../mini-program'),
  
  // 版本号
  version: process.env.VERSION || '1.0.0',
  
  // 版本描述
  desc: process.env.VERSION_DESC || '林麝健康监测小程序',
};

// 检查配置
function checkConfig() {
  console.log('📋 配置信息:');
  console.log(`  AppID: ${CONFIG.appid}`);
  console.log(`  项目路径: ${CONFIG.projectPath}`);
  console.log(`  私钥路径: ${CONFIG.privateKeyPath}`);
  console.log(`  版本号: ${CONFIG.version}`);
  console.log(`  版本描述: ${CONFIG.desc}`);
  console.log('');

  // 检查项目路径
  if (!fs.existsSync(CONFIG.projectPath)) {
    console.error(`❌ 项目路径不存在: ${CONFIG.projectPath}`);
    process.exit(1);
  }

  // 检查 app.json 是否存在
  const appJsonPath = path.join(CONFIG.projectPath, 'app.json');
  if (!fs.existsSync(appJsonPath)) {
    console.error(`❌ app.json 不存在: ${appJsonPath}`);
    process.exit(1);
  }

  // 检查私钥文件
  if (!fs.existsSync(CONFIG.privateKeyPath)) {
    console.error(`❌ 私钥文件不存在: ${CONFIG.privateKeyPath}`);
    console.error('   请从微信小程序后台下载上传密钥');
    console.error('   路径: 开发管理 -> 开发设置 -> 小程序代码上传');
    process.exit(1);
  }

  console.log('✅ 配置检查通过\n');
}

// 上传小程序
async function upload() {
  try {
    checkConfig();

    console.log('🚀 开始上传小程序...\n');

    // 创建项目对象
    const project = new ci.Project({
      appid: CONFIG.appid,
      type: 'miniProgram',
      projectPath: CONFIG.projectPath,
      privateKeyPath: CONFIG.privateKeyPath,
      ignores: ['node_modules/**/*', '**/node_modules/**/*'],
    });

    // 执行上传
    const uploadResult = await ci.upload({
      project,
      version: CONFIG.version,
      desc: CONFIG.desc,
      setting: {
        es6: true,
        es7: true,
        minify: true,
        codeProtect: false,
        minifyJS: true,
        minifyWXML: true,
        minifyWXSS: true,
        autoPrefixWXSS: true,
      },
      onProgressUpdate: (info) => {
        if (info._msg) {
          console.log(`  ${info._msg}`);
        }
      },
    });

    console.log('\n✅ 上传成功!');
    console.log('📦 上传结果:');
    console.log(`  版本: ${uploadResult.subPackageInfo?.[0]?.name || 'main'}`);
    console.log(`  大小: ${(uploadResult.pluginSize / 1024).toFixed(2)} KB`);
    
    return uploadResult;
  } catch (error) {
    console.error('\n❌ 上传失败:');
    console.error(error.message);
    if (error.stack) {
      console.error('\n详细错误:');
      console.error(error.stack);
    }
    process.exit(1);
  }
}

// 预览小程序
async function preview() {
  try {
    checkConfig();

    console.log('🚀 开始生成预览二维码...\n');

    const project = new ci.Project({
      appid: CONFIG.appid,
      type: 'miniProgram',
      projectPath: CONFIG.projectPath,
      privateKeyPath: CONFIG.privateKeyPath,
      ignores: ['node_modules/**/*', '**/node_modules/**/*'],
    });

    const previewResult = await ci.preview({
      project,
      desc: CONFIG.desc,
      setting: {
        es6: true,
        es7: true,
        minify: true,
        codeProtect: false,
      },
      qrcodeFormat: 'image',
      qrcodeOutputDest: path.join(__dirname, 'preview-qrcode.png'),
      onProgressUpdate: (info) => {
        if (info._msg) {
          console.log(`  ${info._msg}`);
        }
      },
    });

    console.log('\n✅ 预览二维码生成成功!');
    console.log(`📱 二维码保存至: ${path.join(__dirname, 'preview-qrcode.png')}`);
    
    return previewResult;
  } catch (error) {
    console.error('\n❌ 预览失败:');
    console.error(error.message);
    process.exit(1);
  }
}

// 主函数
async function main() {
  const command = process.argv[2] || 'upload';
  
  switch (command) {
    case 'upload':
      await upload();
      break;
    case 'preview':
      await preview();
      break;
    default:
      console.log('用法: node upload-miniprogram.js [upload|preview]');
      console.log('  upload  - 上传小程序到微信后台');
      console.log('  preview - 生成预览二维码');
      process.exit(0);
  }
}

// 执行
main();
