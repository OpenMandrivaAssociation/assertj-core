Name:		assertj-core
Version:	3.27.7
Release:	1
Summary:	Fluent assertions for Java tests
Group:		Development/Java
License:	Apache-2.0
URL:		https://assertj.github.io/doc/#assertj-core
Source0:	https://codeload.github.com/assertj/assertj/tar.gz/refs/tags/assertj-build-%{version}#/assertj-build-%{version}.tar.gz
BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	python
BuildRequires:	sysjar
BuildRequires:	mvn(net.bytebuddy:byte-buddy)
BuildRequires:	mvn(org.ow2.asm:asm)
BuildRequires:	mvn(org.ow2.asm:asm-commons)
BuildRequires:	mvn(junit:junit)
BuildRequires:	mvn(org.hamcrest:hamcrest)
BuildRequires:	mvn(org.opentest4j:opentest4j)

%description
AssertJ provides fluent assertions for Java tests. Soft assertions and
assumptions generate their proxies with the system copy of Byte Buddy.
The JUnit 4 rule and the Hamcrest condition are included. The JUnit
Jupiter extension is not.

%prep
%setup -q -n assertj-assertj-build-%{version}
find . -name '*.class' -delete
find . -name '*.jar' -delete
if find . \( -name '*.class' -o -name '*.jar' \) | grep -q .; then
	echo "prebuilt bytecode remains" >&2
	exit 1
fi
rm -f \
	assertj-core/src/main/java/org/assertj/core/api/junit/jupiter/InjectSoftAssertions.java \
	assertj-core/src/main/java/org/assertj/core/api/junit/jupiter/SoftAssertionsExtension.java \
	assertj-core/src/main/java/org/assertj/core/api/junit/jupiter/SoftlyExtension.java \
	assertj-core/src/main/java/org/assertj/core/api/JUnitJupiterBDDSoftAssertions.java \
	assertj-core/src/main/java/org/assertj/core/api/JUnitJupiterSoftAssertions.java

%build
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java}"
CP=/usr/share/java/byte-buddy.jar:/usr/share/java/junit.jar:/usr/share/java/hamcrest/hamcrest.jar:/usr/share/java/opentest4j/opentest4j.jar
mkdir -p build/classes
find assertj-core/src/main/java -name '*.java' | sort > build/sources.list
python - << 'PY'
from pathlib import Path
lines = Path("build/sources.list").read_text().splitlines()
if len(lines) != 787:
    raise SystemExit("source count " + str(len(lines)))
banned = ("InjectSoftAssertions.java", "SoftAssertionsExtension.java", "SoftlyExtension.java", "JUnitJupiterBDDSoftAssertions.java", "JUnitJupiterSoftAssertions.java", "module-info.java")
if any(name.endswith(banned) for name in lines):
    raise SystemExit("excluded source still listed")
PY
"$JAVA_HOME/bin/javac" --release 8 -encoding UTF-8 -cp "$CP" \
	-d build/classes @build/sources.list
python - << 'PY'
from pathlib import Path
root = Path("build/classes")
count = 0
for path in root.rglob("*.class"):
    data = path.read_bytes()
    major = int.from_bytes(data[6:8], "big")
    if major != 52:
        raise SystemExit(str(path) + " has major " + str(major))
    count += 1
if count != 836:
    raise SystemExit("class count " + str(count))
PY
cat > build/manifest.mf << 'EOF'
Manifest-Version: 1.0
Implementation-Title: org.assertj.core
Implementation-Version: %{version}
Specification-Title: AssertJ Core
Specification-Version: %{version}
Automatic-Module-Name: org.assertj.core

EOF
"$JAVA_HOME/bin/jar" --create --manifest build/manifest.mf \
	--file build/assertj-core.jar -C build/classes .
cat > build/assertj-core.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.assertj</groupId>
  <artifactId>assertj-core</artifactId>
  <version>%{version}</version>
  <name>AssertJ Core</name>
  <description>Fluent assertions built against the system Byte Buddy.</description>
  <url>https://assertj.github.io/doc/#assertj-core</url>
  <licenses>
    <license>
      <name>Apache License, Version 2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>net.bytebuddy</groupId>
      <artifactId>byte-buddy</artifactId>
      <version>1.18.17</version>
    </dependency>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
      <scope>provided</scope>
      <optional>true</optional>
    </dependency>
    <dependency>
      <groupId>org.hamcrest</groupId>
      <artifactId>hamcrest</artifactId>
      <version>3.0</version>
      <scope>provided</scope>
      <optional>true</optional>
    </dependency>
    <dependency>
      <groupId>org.opentest4j</groupId>
      <artifactId>opentest4j</artifactId>
      <version>1.3.0</version>
      <scope>provided</scope>
      <optional>true</optional>
    </dependency>
  </dependencies>
</project>
EOF

%install
sysjar install --buildroot %{buildroot} \
	--artifact build/assertj-core.pom:build/assertj-core.jar \
	--file-name assertj-core \
	--filelist .mfiles

%check
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java}"
"$JAVA_HOME/bin/jar" tf build/assertj-core.jar > build/jar-list.txt
for class in \
	org/assertj/core/api/Assertions.class \
	org/assertj/core/api/SoftAssertions.class \
	org/assertj/core/api/SoftAssertionsRule.class \
	org/assertj/core/api/HamcrestCondition.class
do
	if ! grep -F -x -q "$class" build/jar-list.txt; then
		echo "missing $class" >&2
		exit 1
	fi
done
if grep -F -e SoftAssertionsExtension -e SoftlyExtension -e InjectSoftAssertions -e JUnitJupiter -e module-info.class build/jar-list.txt; then
	echo "jar contains an excluded class" >&2
	exit 1
fi
"$JAVA_HOME/bin/jar" --describe-module --file build/assertj-core.jar > build/module.txt
if ! grep -F -q 'org.assertj.core automatic' build/module.txt; then
	echo "automatic module name" >&2
	exit 1
fi
mkdir -p build/probe
cat > build/Probe.java << 'EOF'
import org.assertj.core.api.Assertions;
import org.assertj.core.api.SoftAssertions;

public class Probe {
	public static void main(String[] args) {
		Assertions.assertThat(2 + 2).isEqualTo(4);
		Assertions.assertThat("AssertJ").startsWith("Assert");
		SoftAssertions softly = new SoftAssertions();
		softly.assertThat("ab").contains("a");
		softly.assertAll();
		System.out.println("probe ok");
	}
}
EOF
"$JAVA_HOME/bin/javac" --release 8 -encoding UTF-8 \
	-cp build/assertj-core.jar -d build/probe build/Probe.java
"$JAVA_HOME/bin/java" --enable-native-access=ALL-UNNAMED \
	-cp "build/probe:build/assertj-core.jar:/usr/share/java/byte-buddy.jar:/usr/share/java/asm.jar:/usr/share/java/asm-commons.jar:/usr/share/java/opentest4j/opentest4j.jar" \
	Probe > build/probe.out
if ! grep -F -x -q 'probe ok' build/probe.out; then
	echo "probe failed" >&2
	exit 1
fi

%files -f .mfiles
%license LICENSE.txt
%doc README.md
