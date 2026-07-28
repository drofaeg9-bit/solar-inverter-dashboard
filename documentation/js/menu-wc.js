'use strict';

customElements.define('compodoc-menu', class extends HTMLElement {
    constructor() {
        super();
        this.isNormalMode = this.getAttribute('mode') === 'normal';
    }

    connectedCallback() {
        this.render(this.isNormalMode);
    }

    render(isNormalMode) {
        let tp = lithtml.html(`
        <nav>
            <ul class="list">
                <li class="title">
                    <a href="index.html" data-type="index-link">Solar Inverter Dashboard</a>
                </li>

                <li class="divider"></li>
                ${ isNormalMode ? `<div id="book-search-input" role="search"><input type="text" placeholder="Type to search"></div>` : '' }
                <li class="chapter">
                    <a data-type="chapter-link" href="index.html"><span class="icon ion-ios-home"></span>Getting started</a>
                    <ul class="links">
                                <li class="link">
                                    <a href="overview.html" data-type="chapter-link">
                                        <span class="icon ion-ios-keypad"></span>Overview
                                    </a>
                                </li>

                            <li class="link">
                                <a href="index.html" data-type="chapter-link">
                                    <span class="icon ion-ios-paper"></span>
                                        README
                                </a>
                            </li>
                                <li class="link">
                                    <a href="properties.html" data-type="chapter-link">
                                        <span class="icon ion-ios-apps"></span>Properties
                                    </a>
                                </li>

                    </ul>
                </li>
                    <li class="chapter additional">
                        <div class="simple menu-toggler" data-bs-toggle="collapse" ${ isNormalMode ? 'data-bs-target="#additional-pages"'
                            : 'data-bs-target="#xs-additional-pages"' }>
                            <span class="icon ion-ios-book"></span>
                            <span>Project Guide</span>
                            <span class="icon ion-ios-arrow-down"></span>
                        </div>
                        <ul class="links collapse " ${ isNormalMode ? 'id="additional-pages"' : 'id="xs-additional-pages"' }>
                                    <li class="link ">
                                        <a href="additional-documentation/project-overview.html" data-type="entity-link" data-context-id="additional">Project overview</a>
                                    </li>
                                    <li class="link ">
                                        <a href="additional-documentation/architecture.html" data-type="entity-link" data-context-id="additional">Architecture</a>
                                    </li>
                                    <li class="link ">
                                        <a href="additional-documentation/dashboard-api.html" data-type="entity-link" data-context-id="additional">Dashboard API</a>
                                    </li>
                                    <li class="link ">
                                        <a href="additional-documentation/home-assistant-integration.html" data-type="entity-link" data-context-id="additional">Home Assistant integration</a>
                                    </li>
                                    <li class="chapter inner">
                                        <a data-type="chapter-link" href="additional-documentation/operations.html" data-context-id="additional">
                                            <div class="menu-toggler linked" data-bs-toggle="collapse" ${ isNormalMode ?
                                            'data-bs-target="#additional-page-3c347b2524346a3c78f00d2cd596aa5bf8d1caadc11c0ac3ab3d9ff9fda3449077b653db359c82a6d861725a8a7659306ed8d888c93d88d6f11f452788cc51d9"' : 'data-bs-target="#xs-additional-page-3c347b2524346a3c78f00d2cd596aa5bf8d1caadc11c0ac3ab3d9ff9fda3449077b653db359c82a6d861725a8a7659306ed8d888c93d88d6f11f452788cc51d9"' }>
                                                <span class="link-name">Operations</span>
                                                <span class="icon ion-ios-arrow-down"></span>
                                            </div>
                                        </a>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="additional-page-3c347b2524346a3c78f00d2cd596aa5bf8d1caadc11c0ac3ab3d9ff9fda3449077b653db359c82a6d861725a8a7659306ed8d888c93d88d6f11f452788cc51d9"' : 'id="xs-additional-page-3c347b2524346a3c78f00d2cd596aa5bf8d1caadc11c0ac3ab3d9ff9fda3449077b653db359c82a6d861725a8a7659306ed8d888c93d88d6f11f452788cc51d9"' }>
                                            <li class="link for-chapter2">
                                                <a href="additional-documentation/operations/orange-pi-deployment.html" data-type="entity-link" data-context="sub-entity" data-context-id="additional">Orange Pi deployment</a>
                                            </li>
                                        </ul>
                                    </li>
                        </ul>
                    </li>
                    <li class="chapter">
                        <div class="simple menu-toggler" data-bs-toggle="collapse" ${ isNormalMode ? 'data-bs-target="#classes-links"' :
                            'data-bs-target="#xs-classes-links"' }>
                            <span class="icon ion-ios-paper"></span>
                            <span>Classes</span>
                            <span class="icon ion-ios-arrow-down"></span>
                        </div>
                        <ul class="links collapse " ${ isNormalMode ? 'id="classes-links"' : 'id="xs-classes-links"' }>
                            <li class="link">
                                <a href="classes/DashboardApi.html" data-type="entity-link" >DashboardApi</a>
                            </li>
                        </ul>
                    </li>
                    <li class="chapter">
                        <div class="simple menu-toggler" data-bs-toggle="collapse" ${ isNormalMode ? 'data-bs-target="#interfaces-links"' :
                            'data-bs-target="#xs-interfaces-links"' }>
                            <span class="icon ion-md-information-circle-outline"></span>
                            <span>Interfaces</span>
                            <span class="icon ion-ios-arrow-down"></span>
                        </div>
                        <ul class="links collapse " ${ isNormalMode ? ' id="interfaces-links"' : 'id="xs-interfaces-links"' }>
                            <li class="link">
                                <a href="interfaces/DashboardSettingsUpdate.html" data-type="entity-link" >DashboardSettingsUpdate</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/DashboardState.html" data-type="entity-link" >DashboardState</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/RegisterLogStatus.html" data-type="entity-link" >RegisterLogStatus</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/RegisterReading.html" data-type="entity-link" >RegisterReading</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/SolarEnergySummary.html" data-type="entity-link" >SolarEnergySummary</a>
                            </li>
                        </ul>
                    </li>
                    <li class="chapter">
                        <div class="simple menu-toggler" data-bs-toggle="collapse" ${ isNormalMode ? 'data-bs-target="#miscellaneous-links"'
                            : 'data-bs-target="#xs-miscellaneous-links"' }>
                            <span class="icon ion-ios-cube"></span>
                            <span>Miscellaneous</span>
                            <span class="icon ion-ios-arrow-down"></span>
                        </div>
                        <ul class="links collapse " ${ isNormalMode ? 'id="miscellaneous-links"' : 'id="xs-miscellaneous-links"' }>
                            <li class="link">
                                <a href="miscellaneous/enumerations.html" data-type="entity-link">Enums</a>
                            </li>
                            <li class="link">
                                <a href="miscellaneous/typealiases.html" data-type="entity-link">Type aliases</a>
                            </li>
                        </ul>
                    </li>
                        <li class="chapter">
                            <a data-type="chapter-link" href="routes.html"><span class="icon ion-ios-git-branch"></span>Routes</a>
                        </li>
                    <li class="chapter">
                        <a data-type="chapter-link" href="coverage.html"><span class="icon ion-ios-stats"></span>Documentation coverage</a>
                    </li>
                    <li class="divider"></li>
                    <li class="copyright">
                        Documentation generated using <a href="https://compodoc.app/" target="_blank" rel="noopener noreferrer">
                            <img data-src="images/compodoc-vectorise-inverted.png" class="img-responsive" data-type="compodoc-logo">
                        </a>
                    </li>
            </ul>
        </nav>
        `);
        this.innerHTML = tp.strings;
    }
});