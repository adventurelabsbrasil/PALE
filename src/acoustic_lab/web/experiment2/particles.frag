uniform vec3 uColor;
varying float vAlpha;
varying float vNovelty;
void main(){vec2 p=gl_PointCoord-.5;float a=smoothstep(.5,0.0,length(p));vec3 color=mix(uColor,vec3(1.0,.55,.8),vNovelty*.7);gl_FragColor=vec4(color,a*vAlpha);}
