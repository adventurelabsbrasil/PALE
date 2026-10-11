uniform float uTime;
uniform vec3 uColor;
uniform float uSilence;
uniform float uRepeat;
varying float vEnergy;
varying float vRim;
varying float vNovelty;
varying float vNote;
void main(){
  float pulse=.72+sin(uTime*1.7)*.08+vEnergy*.25;
  vec3 color=mix(uColor,vec3(1.0,.54,.84),vNovelty*.7); color=mix(color,vec3(.34,.28,1.0),uRepeat*.35); color=mix(color,vec3(.96,.88,.48),vNote);
  float alpha=(.07+vRim*.24)*pulse*(1.0-uSilence*.5)+vNote*.32;
  gl_FragColor=vec4(color,alpha);
}
