uniform float uTime;
uniform vec4 uFeatures;
uniform float uSilence;
uniform float uRepeat;
uniform float uNovelty;
uniform vec3 uNoteBand;
uniform float uNotePulse;
varying float vEnergy;
varying float vRim;
varying float vNovelty;
varying float vNote;

float hash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}

void main(){
  float energy=uFeatures.x, low=uFeatures.y, high=uFeatures.z, flux=uFeatures.w;
  float n=noise(normal*2.2+uTime*vec3(.18,.13,.11)*(.35+high));
  float wave=sin(atan(position.y,position.x)*8.0+uTime*(1.0+flux*6.0)+position.z*5.0)*flux*.1;
  float branching=sin(position.x*9.0+position.y*7.0+uTime*.4)*uNovelty*.08;
  float amount=(.035+energy*.19+low*.13+wave+n*.075+branching)*(1.0-uSilence*.58)+uRepeat*.045;
  vec3 displaced=position+normal*amount;
  vec4 mvPosition=modelViewMatrix*vec4(displaced,1.0);
  gl_Position=projectionMatrix*mvPosition;
  vEnergy=energy; vNovelty=uNovelty; vNote=pow(max(dot(normalize(position),normalize(uNoteBand)),0.0),24.0)*uNotePulse;
  vRim=1.0-max(0.0,dot(normalize(normalMatrix*normal),normalize(-mvPosition.xyz)));
}
