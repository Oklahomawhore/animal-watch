// components/ec-canvas/ec-canvas.js
import * as echarts from './echarts';

let ctx;

Component({
  properties: {
    canvasId: {
      type: String,
      value: 'ec-canvas'
    },
    ec: {
      type: Object
    }
  },

  data: {
    isUse2dCanvas: false
  },

  ready() {
    // 检查是否支持 2D Canvas
    const { SDKVersion } = wx.getSystemInfoSync();
    const canUseNewCanvas = this.compareVersion(SDKVersion, '2.9.0') >= 0;
    this.setData({ isUse2dCanvas: canUseNewCanvas });
    
    if (!this.data.ec) {
      console.warn('组件需要传入 ec 对象，包含 init 方法');
      return;
    }
    
    this.init();
  },

  methods: {
    init() {
      const { canvasId } = this.data;
      
      if (this.data.isUse2dCanvas) {
        this.initByNew(canvasId);
      } else {
        this.initByOld(canvasId);
      }
    },

    initByOld(canvasId) {
      ctx = wx.createCanvasContext(canvasId, this);
      const canvas = {
        width: 0,
        height: 0,
        getContext: () => ctx,
        setWidth: (w) => { canvas.width = w; },
        setHeight: (h) => { canvas.height = h; }
      };
      
      echarts.setCanvasCreator(() => canvas);
      
      if (typeof this.data.ec.init === 'function') {
        this.chart = this.data.ec.init(canvas, null, {
          width: this.data.width,
          height: this.data.height
        });
      }
    },

    initByNew(canvasId) {
      const query = wx.createSelectorQuery().in(this);
      query.select('.ec-canvas').fields({ node: true, size: true }).exec((res) => {
        const canvasNode = res[0].node;
        const canvasDpr = wx.getSystemInfoSync().pixelRatio;
        const canvasWidth = res[0].width;
        const canvasHeight = res[0].height;
        
        const ctx = canvasNode.getContext('2d');
        
        const canvas = {
          width: canvasWidth,
          height: canvasHeight,
          getContext: () => ctx,
          setWidth: (w) => { canvas.width = w; },
          setHeight: (h) => { canvas.height = h; }
        };
        
        echarts.setCanvasCreator(() => canvas);
        
        if (typeof this.data.ec.init === 'function') {
          this.chart = this.data.ec.init(canvas, null, {
            width: canvasWidth,
            height: canvasHeight,
            devicePixelRatio: canvasDpr
          });
        }
      });
    },

    canvasToTempFilePath(opt) {
      if (this.data.isUse2dCanvas) {
        const query = wx.createSelectorQuery().in(this);
        query.select('.ec-canvas').fields({ node: true, size: true }).exec((res) => {
          const canvasNode = res[0].node;
          wx.canvasToTempFilePath({
            canvas: canvasNode,
            ...opt
          });
        });
      } else {
        ctx.canvasToTempFilePath(opt);
      }
    },

    touchStart(e) {
      if (this.chart && e.touches.length > 0) {
        const touch = e.touches[0];
        const handler = this.chart.getZr().handler;
        handler.dispatch('mousedown', {
          zrX: touch.x,
          zrY: touch.y
        });
        handler.dispatch('mousemove', {
          zrX: touch.x,
          zrY: touch.y
        });
      }
    },

    touchMove(e) {
      if (this.chart && e.touches.length > 0) {
        const touch = e.touches[0];
        const handler = this.chart.getZr().handler;
        handler.dispatch('mousemove', {
          zrX: touch.x,
          zrY: touch.y
        });
      }
    },

    touchEnd(e) {
      if (this.chart) {
        const handler = this.chart.getZr().handler;
        handler.dispatch('mouseup', {});
      }
    },

    compareVersion(v1, v2) {
      const v1Arr = v1.split('.');
      const v2Arr = v2.split('.');
      const len = Math.max(v1Arr.length, v2Arr.length);
      
      while (v1Arr.length < len) {
        v1Arr.push('0');
      }
      while (v2Arr.length < len) {
        v2Arr.push('0');
      }
      
      for (let i = 0; i < len; i++) {
        const num1 = parseInt(v1Arr[i]);
        const num2 = parseInt(v2Arr[i]);
        
        if (num1 > num2) {
          return 1;
        } else if (num1 < num2) {
          return -1;
        }
      }
      
      return 0;
    }
  }
});
