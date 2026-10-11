uniform vec3 uColor;
uniform float uAlpha;
varying float vAlong;
varying float vSignal;
void main(){float fade=.12+.88*clamp(vAlong,0.0,1.0);vec3 color=mix(uColor,vec3(1.0,.55,.82),clamp(vSignal*.45,0.0,1.0));gl_FragColor=vec4(color,fade*uAlpha);}
