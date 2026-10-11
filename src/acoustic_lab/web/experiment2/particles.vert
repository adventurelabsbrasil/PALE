uniform float uTime;
uniform float uEnergy;
uniform float uDensity;
uniform float uRepeat;
uniform float uNovelty;
attribute float aSeed;
varying float vAlpha;
varying float vNovelty;
void main(){vec3 p=position;float a=aSeed*6.28318+uTime*(.08+aSeed*.3);float r=1.1+aSeed*2.2+uEnergy*.5+uNovelty*.45;p+=vec3(cos(a),sin(a*.73),sin(a))*r*.18;p+=normalize(p)*sin(a*3.0+uTime)*uNovelty*.18;vec4 mv=modelViewMatrix*vec4(p,1.0);gl_Position=projectionMatrix*mv;gl_PointSize=(1.0+uDensity*3.0+uNovelty*2.0)*(38.0/-mv.z);vAlpha=.12+.5*uDensity+.22*uRepeat;vNovelty=uNovelty;}
