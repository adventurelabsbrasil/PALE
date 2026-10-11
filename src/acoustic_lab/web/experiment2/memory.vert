uniform float uTime;
uniform float uEnergy;
uniform float uRepeat;
uniform float uNovelty;
varying float vAlong;
varying float vSignal;
void main(){vAlong=position.z*.5+.5;vSignal=uRepeat+uNovelty;vec3 p=position;p*=1.0+sin(uTime*.7+position.z*8.0)*uEnergy*.035;gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);}
