/* Input: mono Float32 at an explicitly checked 24 kHz AudioContext.
   Output: 20 ms chunks of raw PCM16 little-endian. Speaker output is silence. */
class RelayCapture extends AudioWorkletProcessor {
  constructor(){ super(); this.samples=new Float32Array(480); this.offset=0; }
  process(inputs,outputs){
    for(const output of outputs)for(const channel of output)channel.fill(0);
    const input=inputs[0]?.[0];if(!input)return true;
    for(const sample of input){
      this.samples[this.offset++]=Math.max(-1,Math.min(1,sample));
      if(this.offset===480){
        const buffer=new ArrayBuffer(960),view=new DataView(buffer);
        for(let i=0;i<480;i++){const value=this.samples[i];view.setInt16(i*2,Math.round(value*(value<0?32768:32767)),true);}
        this.port.postMessage(buffer,[buffer]);this.offset=0;
      }
    }
    return true;
  }
}
registerProcessor('relay-capture',RelayCapture);
