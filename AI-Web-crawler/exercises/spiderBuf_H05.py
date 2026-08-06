# coding=utf-8

import base64

import hashlib

import json

import time

from pathlib import Path



import requests

from lxml import etree

# selenium 只在备选方案里用，放到函数里再 import，没装也不影响接口方案


# <script type="text/javascript" src="/static/js/md5.min.js"></script>
# <script type="text/javascript" src="/static/js/3NjU0MzIx.min.js"></script>

# 解析：https://spiderbuf.cn/static/js/3NjU0MzIx.min.js
# var _0x5b5a = ['a2JLbWk=', 'UG53dWQ=', 'bkFFSFY=', 'dGFibGU=', 'XihbXiBdKyggK1teIF0rKSspK1teIF19', 'NXwwfDF8Mnw0fDl8OHw3fDZ8Mw==', 'dHJ1bmM=', 'Z3NBamE=', 'aUliTVA=', 'QXljVHM=', 'dXNlZF9jb3VudA==', 'dGltZV90b19jcmFja19pdA==', 'dHJhY2U=', 'bG9n', 'U2ZmRlo=', 'bFhPTkw=', 'c3BsaXQ=', 'cmV0dXJuIChmdW5jdGlvbigpIA==', 'bVJ2SFM=', 'ZXhjZXB0aW9u', 'aW5uZXJUZXh0', 'aW5mbw==', 'S0hjSGQ=', 'WFl6bFg=', 'dGVzdA==', 'cmFua2luZw==', 'ZGF0YUNvbnRlbnQ=', 'RUZZQnM=', 'dGhlbg==', 'Z2V0VGltZQ==', 'MHwzfDJ8MXw1fDd8Nnw0', 'dHRGYXQ=', 'bFFEQm0=', 'V3dvWG4=', 'cGFzc3dk', 'TXloUnA=', 'aW5zZXJ0Um93', 'QlJWWUk=', 'ZXJyb3I=', 'aU13RWI=', 'anNvbg==', 'TWRxbEY=', 'd2Fybg==', 'Z2V0RWxlbWVudEJ5SWQ=', 'NHwzfDV8MHwyfDd8OHwxfDY=', 'aW5zZXJ0Q2VsbA==', 'Y29uc29sZQ==', 'Zm9yRWFjaA==', 'MXwyfDd8NHw2fDB8NXwz', 'WVVxYUY=', 'YXBwbHk=', 'Z3pqbEo=', 'ZGVidWc=', 'cmV0dXJuIC8iICsgdGhpcyArICIv', 'QlRaSGY='];
# (function(_0x55b1a6, _0x5b5add) {
#     var _0x1d6c11 = function(_0xcec9d2) {
#         while (--_0xcec9d2) {
#             _0x55b1a6['push'](_0x55b1a6['shift']());
#         }
#     };
#     var _0x53bcfb = function() {
#         var _0x2b4fb2 = {
#             'data': {
#                 'key': 'cookie',
#                 'value': 'timeout'
#             },
#             'setCookie': function(_0x254b44, _0x11ae2a, _0x52e06c, _0x335182) {
#                 _0x335182 = _0x335182 || {};
#                 var _0x3555da = _0x11ae2a + '=' + _0x52e06c;
#                 var _0xf07877 = 0x0;
#                 for (var _0x57799f = 0x0, _0x3a01cb = _0x254b44['length']; _0x57799f < _0x3a01cb; _0x57799f++) {
#                     var _0x5a0dd2 = _0x254b44[_0x57799f];
#                     _0x3555da += ';\x20' + _0x5a0dd2;
#                     var _0x292cfc = _0x254b44[_0x5a0dd2];
#                     _0x254b44['push'](_0x292cfc);
#                     _0x3a01cb = _0x254b44['length'];
#                     if (_0x292cfc !== !![]) {
#                         _0x3555da += '=' + _0x292cfc;
#                     }
#                 }
#                 _0x335182['cookie'] = _0x3555da;
#             },
#             'removeCookie': function() {
#                 return 'dev';
#             },
#             'getCookie': function(_0x3833a9, _0x42192c) {
#                 _0x3833a9 = _0x3833a9 || function(_0x5e332a) {
#                     return _0x5e332a;
#                 }
#                 ;
#                 var _0xae600a = _0x3833a9(new RegExp('(?:^|;\x20)' + _0x42192c['replace'](/([.$?*|{}()[]\/+^])/g, '$1') + '=([^;]*)'));
#                 var _0x58368f = function(_0x36e467, _0x33acbb) {
#                     _0x36e467(++_0x33acbb);
#                 };
#                 _0x58368f(_0x1d6c11, _0x5b5add);
#                 return _0xae600a ? decodeURIComponent(_0xae600a[0x1]) : undefined;
#             }
#         };
#         var _0x1eabd7 = function() {
#             var _0x34e926 = new RegExp('\x5cw+\x20*\x5c(\x5c)\x20*{\x5cw+\x20*[\x27|\x22].+[\x27|\x22];?\x20*}');
#             return _0x34e926['test'](_0x2b4fb2['removeCookie']['toString']());
#         };
#         _0x2b4fb2['updateCookie'] = _0x1eabd7;
#         var _0x2080f9 = '';
#         var _0x5c3554 = _0x2b4fb2['updateCookie']();
#         if (!_0x5c3554) {
#             _0x2b4fb2['setCookie'](['*'], 'counter', 0x1);
#         } else if (_0x5c3554) {
#             _0x2080f9 = _0x2b4fb2['getCookie'](null, 'counter');
#         } else {
#             _0x2b4fb2['removeCookie']();
#         }
#     };
#     _0x53bcfb();
# }(_0x5b5a, 0x1cc));
# var _0x1d6c = function(_0x55b1a6, _0x5b5add) {
#     _0x55b1a6 = _0x55b1a6 - 0x0;
#     var _0x1d6c11 = _0x5b5a[_0x55b1a6];
#     if (_0x1d6c['MSLQCF'] === undefined) {
#         (function() {
#             var _0xcec9d2 = function() {
#                 var _0x2080f9;
#                 try {
#                     _0x2080f9 = Function('return\x20(function()\x20' + '{}.constructor(\x22return\x20this\x22)(\x20)' + ');')();
#                 } catch (_0x5c3554) {
#                     _0x2080f9 = window;
#                 }
#                 return _0x2080f9;
#             };
#             var _0x2b4fb2 = _0xcec9d2();
#             var _0x1eabd7 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
#             _0x2b4fb2['atob'] || (_0x2b4fb2['atob'] = function(_0x254b44) {
#                 var _0x11ae2a = String(_0x254b44)['replace'](/=+$/, '');
#                 var _0x52e06c = '';
#                 for (var _0x335182 = 0x0, _0x3555da, _0xf07877, _0x57799f = 0x0; _0xf07877 = _0x11ae2a['charAt'](_0x57799f++); ~_0xf07877 && (_0x3555da = _0x335182 % 0x4 ? _0x3555da * 0x40 + _0xf07877 : _0xf07877,
#                 _0x335182++ % 0x4) ? _0x52e06c += String['fromCharCode'](0xff & _0x3555da >> (-0x2 * _0x335182 & 0x6)) : 0x0) {
#                     _0xf07877 = _0x1eabd7['indexOf'](_0xf07877);
#                 }
#                 return _0x52e06c;
#             }
#             );
#         }());
#         _0x1d6c['cBEHhY'] = function(_0x3a01cb) {
#             var _0x5a0dd2 = atob(_0x3a01cb);
#             var _0x292cfc = [];
#             for (var _0x3833a9 = 0x0, _0x42192c = _0x5a0dd2['length']; _0x3833a9 < _0x42192c; _0x3833a9++) {
#                 _0x292cfc += '%' + ('00' + _0x5a0dd2['charCodeAt'](_0x3833a9)['toString'](0x10))['slice'](-0x2);
#             }
#             return decodeURIComponent(_0x292cfc);
#         }
#         ;
#         _0x1d6c['gqIwWH'] = {};
#         _0x1d6c['MSLQCF'] = !![];
#     }
#     var _0x53bcfb = _0x1d6c['gqIwWH'][_0x55b1a6];
#     if (_0x53bcfb === undefined) {
#         var _0xae600a = function(_0x58368f) {
#             this['IxLxDm'] = _0x58368f;
#             this['OBdMiT'] = [0x1, 0x0, 0x0];
#             this['xcbkiE'] = function() {
#                 return 'newState';
#             }
#             ;
#             this['firYPL'] = '\x5cw+\x20*\x5c(\x5c)\x20*{\x5cw+\x20*';
#             this['KsOlNY'] = '[\x27|\x22].+[\x27|\x22];?\x20*}';
#         };
#         _0xae600a['prototype']['tQhevl'] = function() {
#             var _0x5e332a = new RegExp(this['firYPL'] + this['KsOlNY']);
#             var _0x36e467 = _0x5e332a['test'](this['xcbkiE']['toString']()) ? --this['OBdMiT'][0x1] : --this['OBdMiT'][0x0];
#             return this['olqkXh'](_0x36e467);
#         }
#         ;
#         _0xae600a['prototype']['olqkXh'] = function(_0x33acbb) {
#             if (!Boolean(~_0x33acbb)) {
#                 return _0x33acbb;
#             }
#             return this['VxCwhm'](this['IxLxDm']);
#         }
#         ;
#         _0xae600a['prototype']['VxCwhm'] = function(_0x34e926) {
#             for (var _0x3ddf17 = 0x0, _0x5c6388 = this['OBdMiT']['length']; _0x3ddf17 < _0x5c6388; _0x3ddf17++) {
#                 this['OBdMiT']['push'](Math['round'](Math['random']()));
#                 _0x5c6388 = this['OBdMiT']['length'];
#             }
#             return _0x34e926(this['OBdMiT'][0x0]);
#         }
#         ;
#         new _0xae600a(_0x1d6c)['tQhevl']();
#         _0x1d6c11 = _0x1d6c['cBEHhY'](_0x1d6c11);
#         _0x1d6c['gqIwWH'][_0x55b1a6] = _0x1d6c11;
#     } else {
#         _0x1d6c11 = _0x53bcfb;
#     }
#     return _0x1d6c11;
# };
# var _0x254b44 = function() {
#     var _0x320b8f = {};
#     _0x320b8f['SffFZ'] = _0x1d6c('0xa');
#     _0x320b8f[_0x1d6c('0x2c')] = 'INirR';
#     var _0x2daae9 = _0x320b8f;
#     var _0x3e4812 = !![];
#     return function(_0x117970, _0xeb036a) {
#         if (_0x2daae9[_0x1d6c('0x2c')] === _0x1d6c('0x24')) {
#             var _0x2135d9 = _0x2daae9[_0x1d6c('0x31')][_0x1d6c('0x33')]('|');
#             var _0x525af5 = 0x0;
#             while (!![]) {
#                 switch (_0x2135d9[_0x525af5++]) {
#                 case '0':
#                     that[_0x1d6c('0x1a')][_0x1d6c('0x30')] = func;
#                     continue;
#                 case '1':
#                     that[_0x1d6c('0x1a')]['info'] = func;
#                     continue;
#                 case '2':
#                     that[_0x1d6c('0x1a')][_0x1d6c('0x20')] = func;
#                     continue;
#                 case '3':
#                     that[_0x1d6c('0x1a')][_0x1d6c('0x16')] = func;
#                     continue;
#                 case '4':
#                     that[_0x1d6c('0x1a')]['trace'] = func;
#                     continue;
#                 case '5':
#                     that[_0x1d6c('0x1a')][_0x1d6c('0x12')] = func;
#                     continue;
#                 case '6':
#                     that[_0x1d6c('0x1a')]['table'] = func;
#                     continue;
#                 case '7':
#                     that[_0x1d6c('0x1a')][_0x1d6c('0x36')] = func;
#                     continue;
#                 }
#                 break;
#             }
#         } else {
#             var _0x1f2f7d = _0x3e4812 ? function() {
#                 if (_0xeb036a) {
#                     var _0x59229e = _0xeb036a[_0x1d6c('0x1e')](_0x117970, arguments);
#                     _0xeb036a = null;
#                     return _0x59229e;
#                 }
#             }
#             : function() {}
#             ;
#             _0x3e4812 = ![];
#             return _0x1f2f7d;
#         }
#     }
#     ;
# }();
# var _0x5c3554 = _0x254b44(this, function() {
#     var _0x2639b3 = {};
#     _0x2639b3[_0x1d6c('0x7')] = _0x1d6c('0x21');
#     _0x2639b3[_0x1d6c('0xc')] = _0x1d6c('0x27');
#     _0x2639b3[_0x1d6c('0x22')] = function(_0x4ba3db) {
#         return _0x4ba3db();
#     }
#     ;
#     var _0x176529 = _0x2639b3;
#     var _0x39e334 = function() {
#         if (_0x1d6c('0x25') !== _0x1d6c('0x25')) {
#             var _0x5d7093 = _0x39e334['constructor']('return\x20/\x22\x20+\x20this\x20+\x20\x22/')()['compile'](_0x1d6c('0x27'));
#             return !_0x5d7093[_0x1d6c('0x4')](_0x5c3554);
#         } else {
#             var _0x183148 = _0x39e334['constructor'](_0x176529[_0x1d6c('0x7')])()['compile'](_0x176529[_0x1d6c('0xc')]);
#             return !_0x183148[_0x1d6c('0x4')](_0x5c3554);
#         }
#     };
#     return _0x176529['BTZHf'](_0x39e334);
# });
# _0x5c3554();
# var _0x2b4fb2 = function() {
#     var _0x204bdb = !![];
#     return function(_0x387420, _0x593549) {
#         var _0x3bc570 = _0x204bdb ? function() {
#             if (_0x593549) {
#                 var _0x2d77f1 = _0x593549[_0x1d6c('0x1e')](_0x387420, arguments);
#                 _0x593549 = null;
#                 return _0x2d77f1;
#             }
#         }
#         : function() {}
#         ;
#         _0x204bdb = ![];
#         return _0x3bc570;
#     }
#     ;
# }();
# var _0xcec9d2 = _0x2b4fb2(this, function() {
#     var _0x526acb = {};
#     _0x526acb[_0x1d6c('0xf')] = _0x1d6c('0x28');
#     _0x526acb['ESTjj'] = function(_0x1e1fa1, _0x28bb10) {
#         return _0x1e1fa1 === _0x28bb10;
#     }
#     ;
#     _0x526acb[_0x1d6c('0x2')] = 'efzFM';
#     _0x526acb['YiYcU'] = _0x1d6c('0x13');
#     _0x526acb[_0x1d6c('0x32')] = function(_0x46b472, _0x418a1a) {
#         return _0x46b472(_0x418a1a);
#     }
#     ;
#     _0x526acb['gsAja'] = function(_0x48adfe, _0x116c6c) {
#         return _0x48adfe + _0x116c6c;
#     }
#     ;
#     _0x526acb[_0x1d6c('0x3')] = _0x1d6c('0x34');
#     _0x526acb[_0x1d6c('0x11')] = '{}.constructor(\x22return\x20this\x22)(\x20)';
#     _0x526acb[_0x1d6c('0xb')] = function(_0x52a3d2) {
#         return _0x52a3d2();
#     }
#     ;
#     _0x526acb['kbKmi'] = 'ZfHZe';
#     _0x526acb[_0x1d6c('0xd')] = function(_0x47a9e5, _0xac1c8c) {
#         return _0x47a9e5 !== _0xac1c8c;
#     }
#     ;
#     _0x526acb[_0x1d6c('0x2b')] = _0x1d6c('0x1f');
#     _0x526acb[_0x1d6c('0x1d')] = _0x1d6c('0x1c');
#     var _0x3ccd05 = _0x526acb;
#     var _0x24837f = function() {};
#     var _0x12650f;
#     try {
#         if (_0x3ccd05['ESTjj'](_0x3ccd05[_0x1d6c('0x2')], _0x3ccd05['YiYcU'])) {
#             return response[_0x1d6c('0x14')]();
#         } else {
#             var _0x43d119 = _0x3ccd05['lXONL'](Function, _0x3ccd05[_0x1d6c('0x2a')](_0x3ccd05['gsAja'](_0x3ccd05[_0x1d6c('0x3')], _0x3ccd05['BRVYI']), ');'));
#             _0x12650f = _0x3ccd05['ttFat'](_0x43d119);
#         }
#     } catch (_0x135864) {
#         _0x12650f = window;
#     }
#     if (!_0x12650f[_0x1d6c('0x1a')]) {
#         if (_0x3ccd05['ESTjj'](_0x3ccd05['kbKmi'], _0x3ccd05[_0x1d6c('0x23')])) {
#             _0x12650f['console'] = function(_0x2df941) {
#                 var _0x60c861 = {};
#                 _0x60c861[_0x1d6c('0x30')] = _0x2df941;
#                 _0x60c861[_0x1d6c('0x16')] = _0x2df941;
#                 _0x60c861[_0x1d6c('0x20')] = _0x2df941;
#                 _0x60c861[_0x1d6c('0x1')] = _0x2df941;
#                 _0x60c861[_0x1d6c('0x12')] = _0x2df941;
#                 _0x60c861[_0x1d6c('0x36')] = _0x2df941;
#                 _0x60c861[_0x1d6c('0x26')] = _0x2df941;
#                 _0x60c861[_0x1d6c('0x2f')] = _0x2df941;
#                 return _0x60c861;
#             }(_0x24837f);
#         } else {
#             var _0x374f31 = {};
#             _0x374f31['MdqlF'] = _0x3ccd05['MyhRp'];
#             var _0x263c82 = _0x374f31;
#             _0x12650f[_0x1d6c('0x1a')] = function(_0x1c7b10) {
#                 var _0x4bfbb1 = _0x263c82[_0x1d6c('0x15')][_0x1d6c('0x33')]('|');
#                 var _0x20c45f = 0x0;
#                 while (!![]) {
#                     switch (_0x4bfbb1[_0x20c45f++]) {
#                     case '0':
#                         _0x15af51[_0x1d6c('0x30')] = _0x1c7b10;
#                         continue;
#                     case '1':
#                         _0x15af51[_0x1d6c('0x16')] = _0x1c7b10;
#                         continue;
#                     case '2':
#                         _0x15af51['debug'] = _0x1c7b10;
#                         continue;
#                     case '3':
#                         return _0x15af51;
#                     case '4':
#                         _0x15af51['info'] = _0x1c7b10;
#                         continue;
#                     case '5':
#                         var _0x15af51 = {};
#                         continue;
#                     case '6':
#                         _0x15af51['trace'] = _0x1c7b10;
#                         continue;
#                     case '7':
#                         _0x15af51[_0x1d6c('0x26')] = _0x1c7b10;
#                         continue;
#                     case '8':
#                         _0x15af51[_0x1d6c('0x36')] = _0x1c7b10;
#                         continue;
#                     case '9':
#                         _0x15af51[_0x1d6c('0x12')] = _0x1c7b10;
#                         continue;
#                     }
#                     break;
#                 }
#             }(_0x24837f);
#         }
#     } else {
#         if (_0x3ccd05[_0x1d6c('0xd')](_0x3ccd05[_0x1d6c('0x2b')], 'gzjlJ')) {
#             var _0x5bd5ae = _0x1d6c('0x18')['split']('|');
#             var _0x5fd0ae = 0x0;
#             while (!![]) {
#                 switch (_0x5bd5ae[_0x5fd0ae++]) {
#                 case '0':
#                     var _0x12953b = _0x46ec0['insertCell']();
#                     continue;
#                 case '1':
#                     var _0x5de9d8 = _0x46ec0[_0x1d6c('0x19')]();
#                     continue;
#                 case '2':
#                     _0x12953b[_0x1d6c('0x0')] = value['passwd'];
#                     continue;
#                 case '3':
#                     var _0x153651 = _0x46ec0[_0x1d6c('0x19')]();
#                     continue;
#                 case '4':
#                     var _0x46ec0 = dataContent['insertRow']();
#                     continue;
#                 case '5':
#                     _0x153651['innerText'] = value[_0x1d6c('0x5')];
#                     continue;
#                 case '6':
#                     _0x5de9d8[_0x1d6c('0x0')] = value[_0x1d6c('0x2d')];
#                     continue;
#                 case '7':
#                     var _0x52b5a1 = _0x46ec0[_0x1d6c('0x19')]();
#                     continue;
#                 case '8':
#                     _0x52b5a1[_0x1d6c('0x0')] = value['time_to_crack_it'];
#                     continue;
#                 }
#                 break;
#             }
#         } else {
#             var _0xba494f = _0x3ccd05['YUqaF'][_0x1d6c('0x33')]('|');
#             var _0x10b154 = 0x0;
#             while (!![]) {
#                 switch (_0xba494f[_0x10b154++]) {
#                 case '0':
#                     _0x12650f[_0x1d6c('0x1a')][_0x1d6c('0x36')] = _0x24837f;
#                     continue;
#                 case '1':
#                     _0x12650f['console'][_0x1d6c('0x30')] = _0x24837f;
#                     continue;
#                 case '2':
#                     _0x12650f['console'][_0x1d6c('0x16')] = _0x24837f;
#                     continue;
#                 case '3':
#                     _0x12650f[_0x1d6c('0x1a')][_0x1d6c('0x2f')] = _0x24837f;
#                     continue;
#                 case '4':
#                     _0x12650f[_0x1d6c('0x1a')]['info'] = _0x24837f;
#                     continue;
#                 case '5':
#                     _0x12650f['console'][_0x1d6c('0x26')] = _0x24837f;
#                     continue;
#                 case '6':
#                     _0x12650f[_0x1d6c('0x1a')][_0x1d6c('0x12')] = _0x24837f;
#                     continue;
#                 case '7':
#                     _0x12650f['console'][_0x1d6c('0x20')] = _0x24837f;
#                     continue;
#                 }
#                 break;
#             }
#         }
#     }
# });
# _0xcec9d2();
# var timeStamp = Math[_0x1d6c('0x29')](new Date()[_0x1d6c('0x9')]() / 0x3e8);
# var _md5 = md5(timeStamp);
# var s = btoa(timeStamp + ',' + _md5);
# fetch('/challenge/javascript-reverse-timestamp/api/' + s)['then'](function(_0x35f53c) {
#     return _0x35f53c[_0x1d6c('0x14')]();
# })[_0x1d6c('0x8')](function(_0x21c749) {
#     var _0x2fab11 = {};
#     _0x2fab11['mRvHS'] = _0x1d6c('0x6');
#     var _0x21990d = _0x2fab11;
#     var _0x4b7d06 = document[_0x1d6c('0x17')](_0x21990d[_0x1d6c('0x35')]);
#     var _0x334455 = _0x4b7d06.querySelector("tbody");
#     _0x21c749[_0x1d6c('0x1b')]( (_0x286071, _0x4948cd) => {
#         var _0x3541a4 = '3|5|8|4|7|1|6|2|0'[_0x1d6c('0x33')]('|');
#         var _0x56aa05 = 0x0;
#         while (!![]) {
#             switch (_0x3541a4[_0x56aa05++]) {
#             case '0':
#                 _0x2284f5[_0x1d6c('0x0')] = _0x286071[_0x1d6c('0x2d')];
#                 continue;
#             case '1':
#                 var _0xd5f324 = _0xeaefe0[_0x1d6c('0x19')]();
#                 continue;
#             case '2':
#                 var _0x2284f5 = _0xeaefe0[_0x1d6c('0x19')]();
#                 continue;
#             case '3':
#                 var _0xeaefe0 = _0x334455[_0x1d6c('0x10')]();
#                 continue;
#             case '4':
#                 var _0x211ead = _0xeaefe0['insertCell']();
#                 continue;
#             case '5':
#                 var _0x5a021a = _0xeaefe0[_0x1d6c('0x19')]();
#                 continue;
#             case '6':
#                 _0xd5f324[_0x1d6c('0x0')] = _0x286071[_0x1d6c('0x2e')];
#                 continue;
#             case '7':
#                 _0x211ead[_0x1d6c('0x0')] = _0x286071[_0x1d6c('0xe')];
#                 continue;
#             case '8':
#                 _0x5a021a['innerText'] = _0x286071[_0x1d6c('0x5')];
#                 continue;
#             }
#             break;
#         }
#     }
#     );
# });


# # 思路
# 上面那一大坨混淆代码，真正干活的只有末尾这四行：
#     var timeStamp = Math.trunc(new Date().getTime() / 1000);   // 秒级时间戳
#     var _md5 = md5(timeStamp);                                  // md5(时间戳的十进制字符串)
#     var s = btoa(timeStamp + ',' + _md5);                       // base64("时间戳,md5")
#     fetch('/challenge/javascript-reverse-timestamp/api/' + s)
# 前面的 _0x5b5a 字符串表、atob 解码、控制台劫持、switch 打乱执行顺序都是障眼法，
# 不用还原也不影响出结果 —— 认准最后那个 fetch 就行。
#
# 服务端会校验：md5 必须和时间戳对得上，且时间戳必须是"现在"
# （实测 -20 秒还能过，-30 秒就返回 400），所以签名只能每次现算，不能写死。
#
# 接口直接返回 JSON，压根不用解析 HTML；页面上的表格反而是 js 拿到 JSON 之后才填进去的。


# 输出目录固定在脚本旁边，不受启动时工作目录影响；不存在就自动建
outdir = Path(__file__).resolve().parent / 'data' / 'h05'
outdir.mkdir(parents=True, exist_ok=True)


base_url = 'https://spiderbuf.cn/challenge/javascript-reverse-timestamp'

api_url = base_url + '/api/'

myheaders = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'}


def buildPayload(timestamp=0):
    """按 js 的算法生成接口签名：base64('秒级时间戳,md5(秒级时间戳)')"""
    if timestamp == 0:
        timestamp = int(time.time())

    md5_hash = hashlib.md5()
    md5_hash.update(str(timestamp).encode('utf-8'))
    md5 = md5_hash.hexdigest()

    s = '%d,%s' % (timestamp, md5)
    return str(base64.b64encode(s.encode('utf-8')), 'utf-8')


def getData(file_name=''):
    """方案一：逆向 js 直接调接口，返回字典列表"""
    resp = requests.get(api_url + buildPayload(), headers=myheaders, timeout=10)
    print('请求接口 %s，返回状态码 %d' % (resp.url, resp.status_code))
    resp.raise_for_status()   # 签名不对或时间戳过期会返回 400，在这里就炸出来
    rows = resp.json()

    if file_name != '':
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    return rows


def getHTMLByBrowser(url, file_name=''):
    """
    方案二：不逆向，让浏览器自己去执行那段 js，读渲染完的页面。
    需要 pip install selenium 并且本机装了 Chrome。
    """
    from selenium import webdriver

    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    client = webdriver.Chrome(options=options)

    try:
        client.get(url)
        time.sleep(5)          # 等 fetch 回来把表格填上
        html = client.page_source
    finally:
        client.quit()          # 中途出错也要关掉浏览器，不然进程会留着

    if file_name != '':
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(html)

    return html


def parseHTML(html, file_name=''):
    """解析浏览器渲染后的表格，配合方案二使用"""
    root = etree.HTML(html)
    trs = root.xpath('//table[@id="dataContent"]//tr')

    lines = []
    for tr in trs:
        tds = tr.xpath('./td')
        if len(tds) == 0:      # 表头那行只有 th，跳过
            continue

        s = ''
        for td in tds:
            s = s + str(td.xpath('string(.)')).strip() + '|'

        print(s)
        lines.append(s)

    # 文件在有内容时才打开，避免 file_name 为空时 f 没定义就 close
    if file_name != '' and len(lines) > 0:
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')

    return lines


if __name__ == '__main__':

    # 方案一：逆向 js，直接请求接口，不用开浏览器
    rows = getData(str(outdir / 'h05.json'))

    with open(str(outdir / 'h05.txt'), 'w', encoding='utf-8') as f:
        for row in rows:
            s = '%s|%s|%s|%s|' % (
                row['ranking'], row['passwd'], row['time_to_crack_it'], row['used_count'])
            print(s)
            f.write(s + '\n')

    print('共 %d 条' % len(rows))

    # 方案二：交给浏览器执行 js，再解析渲染后的表格
    # html = getHTMLByBrowser(base_url, str(outdir / 'h05.html'))
    # parseHTML(html, str(outdir / 'h05.txt'))


# 来源：https://spiderbuf.cn/code/javascript-reverse-timestamp
# 爬虫练习网站：Spiderbuf
